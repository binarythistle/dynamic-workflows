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
    everything_said = " ".join(h["text"] for h in history if h["role"] == "customer").lower()
    tools_used = [h["tool"] for h in recent if h["role"] == "agent"]
    results = {h["tool"]: h["result"] for h in recent if h["role"] == "tool"}
    product_id = re.search(r"product_id: ([\w-]+)", recent[0]["text"]).group(1)
    questions = [h["args"]["question"] for h in recent
                 if h["role"] == "agent" and h["tool"] == "ask_customer"]

    def asked(text: str) -> bool:
        return any(text in q for q in questions)

    def answer_to(text: str) -> str:
        i = next(i for i, q in enumerate(questions) if text in q)
        return replies[i] if i < len(replies) else ""

    if final_turn:
        return end("You're all set. You can get in touch at any time.")

    # 1. See what the product allows; that decides the rest of the path.
    if "get_account_summary" not in tools_used:
        return call("get_account_summary", {"product_id": product_id})
    summary = results["get_account_summary"]

    # 2. A worried customer gets a guide before anything else.
    if (re.search(r"worried|nervous|unsure|not good|uncomfortable|first time|new to",
                  everything_said)
            and "send_guide" not in tools_used):
        return call("send_guide", {"topic": "what happens when markets fall"})

    # 3a. Fixed term: no more payments, so ask about the end of the term instead.
    if not summary["allows_top_ups"]:
        if not asked("fixed for two years"):
            return ask("This account is fixed for two years. When it ends, would you like the "
                       "money paid out to your bank, moved to an Easy Access Cash ISA, "
                       "or to decide later?")
        if "set_maturity_instruction" not in tools_used:
            answer = replies[-1]
            option = ("pay out to bank account" if re.search(r"pay|bank", answer)
                      else "move to Easy Access Cash ISA" if re.search(r"isa|move", answer)
                      else "decide later")
            return call("set_maturity_instruction", {"option": option})
        return end(f"You're all set. {results['set_maturity_instruction']}.")

    # 3b. Accepts payments: one-off or monthly, and how much?
    if not asked("one-off amount"):
        return ask("Would you like to pay in a one-off amount, or set up regular monthly payments?")
    monthly = re.search(r"month|regular|recurring", answer_to("one-off amount")) is not None
    amount = parse_amount(" ".join(replies))
    if amount is None and not monthly:
        amount = parse_amount(everything_said)  # e.g. the lump sum mentioned earlier
    if amount is None:
        if not asked("How much"):
            return ask("How much would you like to pay in each month?" if monthly
                       else "How much would you like to pay in?")
        amount = parse_amount(answer_to("How much"), pound_sign=False)
    if amount is None:
        return end("No problem, you can set up payments whenever you're ready.")
    if "suggest_contribution_plan" not in tools_used:
        return call("suggest_contribution_plan", {
            "product_id": product_id,
            "amount": amount,
            "frequency": "monthly" if monthly else "one-off",
        })
    plan = results["suggest_contribution_plan"]

    # 4. An ISA has a yearly limit, so check it.
    if summary["isa"] and "check_isa_allowance" not in tools_used:
        return call("check_isa_allowance", {})
    if "warning" in plan:
        return end(f"Heads up: {plan['warning'].removesuffix(' Tell the customer.')} "
                   "You may want to pay in a little less.")

    # 5. Regular payers and fund holders are offered a review.
    if monthly or summary["risk"] != "low":
        if not asked("review"):
            return ask("Would you like me to book a review in 12 months to see how it's going?")
        if ("schedule_review" not in tools_used
                and re.search(r"\b(yes|yeah|sure|please|ok)\b", answer_to("review"))):
            return call("schedule_review", {"months": 12})

    guide = " I've also sent you a short guide." if "send_guide" in tools_used else ""
    return end(f"You're all set.{guide} You can change your payments or get in touch at any time.")


def review(recent: list[dict]) -> dict:
    summary = next((h["result"] for h in recent if h["role"] == "tool"
                    and h["tool"] == "get_account_summary"), None)
    if summary is None:
        product_id = re.search(r"product_id: ([\w-]+)", recent[0]["text"]).group(1)
        return call("get_account_summary", {"product_id": product_id})
    return end(f"Hello again! It's time for your review. You hold the {summary['product']}, "
               f"with fees of {summary['fees']}. You can change your payments or get in "
               "touch at any time.")


def parse_amount(text: str, pound_sign: bool = True) -> int | None:
    match = re.search(r"£\s?(\d[\d,]*)" if pound_sign else r"(\d[\d,]*)", text)
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
