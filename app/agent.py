"""The agent: its limits and, until iteration 4, a fake rule-based model.

The fake model stands in for an LLM. It reads the conversation so far and
picks the next tool, so different answers lead to different paths. It runs
inside the decide_next_step Activity, exactly where the real model will go.
"""

import re

# Guardrail: on the last turn the agent must present options, so every
# conversation reaches the handoff.
MAX_TURNS = 12

DISCLAIMER = (
    "This is general guidance, not personal advice. The value of investments "
    "can go down as well as up, and you may get back less than you put in."
)


def fake_decide(history: list[dict], final_turn: bool) -> dict:
    said = " ".join(h["text"] for h in history if h["role"] == "customer").lower()
    calls = [h for h in history if h["role"] == "agent"]
    tools_used = [c["tool"] for c in calls]
    results = [h for h in history if h["role"] == "tool"]

    found = next((r["result"] for r in results if r["tool"] == "search_products"), [])
    details = [r["result"] for r in results if r["tool"] == "get_product_details"]

    if final_turn:
        return present(details or found)

    # 1. Always start with the time horizon.
    if "ask_customer" not in tools_used:
        return ask("How long are you thinking of investing for, and what is the money for?")

    years = parse_years(said)
    short_term = years is not None and years < 5

    # 2. The second question depends on the first answer.
    if tools_used.count("ask_customer") == 1:
        if short_term:
            return ask("Might you need to take money out at short notice, "
                       "or could it be locked away for a while?")
        return ask("Investments rise and fall. How would you feel if yours "
                   "dropped by 20% in a bad year?")

    # 3. Search with what we have learned.
    if "search_products" not in tools_used:
        return call("search_products", {
            "risk_level": "low" if short_term else parse_risk(said),
            "horizon_years": years if years is not None else 5,
            "needs_access": short_term and "lock" not in said,
        })

    # 4. Only check the ISA allowance if an ISA is on the table.
    if any(p["isa"] for p in found) and "check_isa_allowance" not in tools_used:
        return call("check_isa_allowance", {})

    # 5. Look at each candidate in detail.
    detailed = {d["id"] for d in details}
    for product in found:
        if product["id"] not in detailed:
            return call("get_product_details", {"product_id": product["id"]})

    return present(details)


def parse_years(text: str) -> int | None:
    match = re.search(r"(\d+)\s*(years?|yrs?)", text)
    if match:
        return int(match.group(1))
    if re.search(r"\bmonths?\b", text):
        return 0
    return None


def parse_risk(text: str) -> str:
    if re.search(r"worried|nervous|panic|sell|not happy|upset|lose sleep", text):
        return "low"
    if re.search(r"fine|ok|okay|comfortable|relaxed|happy|don't mind|ride it out", text):
        return "high"
    return "medium"


def ask(question: str) -> dict:
    return call("ask_customer", {"question": question})


def present(products: list[dict]) -> dict:
    return call("present_options", {
        "options": [{"product_id": p["id"], "name": p["name"]} for p in products],
        "explanation": "Based on what you've told me, these options may be worth "
                       "considering. The choice is yours.",
    })


def call(tool: str, args: dict) -> dict:
    return {"tool": tool, "args": args}
