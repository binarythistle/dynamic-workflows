"""A rule-based stand-in for the LLM, for recording without API calls.

It reads the conversation so far and picks the next tool, so different
answers still lead to different paths. Turn it on with USE_FAKE_MODEL=1.
"""

import re


def fake_decide(phase: str, history: list[dict], final_turn: bool) -> dict:
    # Each phase only looks at the conversation since its own start.
    notes = [i for i, h in enumerate(history) if h["role"] == "note"]
    recent = history[notes[-1]:] if notes else history
    match phase:
        case "explore":
            return explore(recent, final_turn)
        case "get_started":
            return get_started(history, recent, final_turn)
        case "review":
            return review(recent)


def explore(history: list[dict], final_turn: bool) -> dict:
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


def get_started(history: list[dict], recent: list[dict], final_turn: bool) -> dict:
    replies = [h["text"].lower() for h in recent if h["role"] == "customer"]
    tools_used = [h["tool"] for h in recent if h["role"] == "agent"]
    product_id = re.search(r"product_id: ([\w-]+)", recent[0]["text"]).group(1)

    if final_turn:
        return end("You're all set. You can change your payments at any time.")

    if "ask_customer" not in tools_used:
        return ask("Would you like to pay in a one-off amount, or set up regular monthly payments?")

    monthly = re.search(r"month|regular", replies[0]) is not None
    if "suggest_contribution_plan" not in tools_used:
        everything_said = " ".join(h["text"] for h in history if h["role"] == "customer")
        return call("suggest_contribution_plan", {
            "amount": parse_amount(replies[0]) or parse_amount(everything_said) or 100,
            "frequency": "monthly" if monthly else "one-off",
        })

    # Only regular savers are offered a review.
    if monthly and tools_used.count("ask_customer") == 1:
        return ask("Would you like me to book a review in 12 months to see how it's going?")
    if (monthly and "schedule_review" not in tools_used
            and re.search(r"\b(yes|yeah|sure|please|ok)\b", replies[-1])):
        return call("schedule_review", {"months": 12})

    if "get_account_summary" not in tools_used:
        return call("get_account_summary", {"product_id": product_id})

    return end("You're all set. You can change your payments or get in touch at any time.")


def review(recent: list[dict]) -> dict:
    summary = next((h["result"] for h in recent if h["role"] == "tool"
                    and h["tool"] == "get_account_summary"), None)
    if summary is None:
        product_id = re.search(r"product_id: ([\w-]+)", recent[0]["text"]).group(1)
        return call("get_account_summary", {"product_id": product_id})
    return end(f"Hello again! It's time for your review. You hold the {summary['product']}, "
               f"with fees of {summary['fees']}. You can change your payments or get in "
               "touch at any time.")


def parse_amount(text: str) -> int | None:
    match = re.search(r"£\s?([\d,]+)", text)
    return int(match.group(1).replace(",", "")) if match else None


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


def end(message: str) -> dict:
    return call("end_conversation", {"message": message})


def call(tool: str, args: dict) -> dict:
    return {"tool": tool, "args": args}
