"""The agent: what it may do, its limits, and the call to the model.

The model only ever picks the next tool. The Workflow runs that tool, records
it, and enforces the rules below. That is "agent chooses, code constrains".

The same agent loop runs in three phases. Each phase has its own prompt, its
own tools, and a tool that must end it.
"""

import json
import os
import re

from openai import AsyncOpenAI

from app.products import PRODUCTS

# Guardrail: on the last turn the agent must present options, so every
# conversation reaches the handoff.
MAX_TURNS = 12

DISCLAIMER = (
    "This is general guidance, not personal advice. The value of investments "
    "can go down as well as up, and you may get back less than you put in."
)

BASE_PROMPT = """\
You are a guidance assistant for a UK investment firm. This is a demo and the
products are made up.

You give general guidance, not a personal recommendation or regulated financial
advice. The customer makes their own choices. Never promise returns. Keep every
message to one to three sentences, and ask one question at a time.
"""

EXPLORE_PROMPT = BASE_PROMPT + """
Help the customer understand which of the firm's products may be worth
considering.

- Ask short clarifying questions with ask_customer, one at a time: what the
  money is for, how long it can be invested, how they feel about falls in
  value, and whether they may need access to it. Ask only what you need.
- Use search_products and get_product_details to find and understand options.
  Only check the ISA allowance if an ISA is being considered.
- Finish with present_options: one to three products from your search results,
  with a plain-English explanation of the trade-offs and risks of each. Do not
  say which one they should choose.
"""

GET_STARTED_PROMPT = BASE_PROMPT + """
The customer has just opened an account (see the latest system note). Help them
get started in a short conversation. What is relevant depends on their product
and on everything they have told you, including earlier in the conversation.

- Start with get_account_summary to see what the product allows.
- If it accepts payments, ask whether they want to pay a one-off amount or
  monthly, and how much. Never assume an amount. Then use
  suggest_contribution_plan, and pass on any warning it returns.
- If it is a fixed-term product, it cannot take more payments. Ask what should
  happen at the end of the term and record it with set_maturity_instruction.
- If they said they would be uncomfortable with falls in value, or that they
  are new to investing, offer a short guide with send_guide.
- If they are paying in monthly, or hold a fund that can fall in value, ask
  whether they would like a review, and only use schedule_review if they agree.
- Finish with end_conversation, briefly summarising what was set up. The
  customer cannot reply to it, so ask any questions with ask_customer first.
"""

REVIEW_PROMPT = BASE_PROMPT + """
The customer's review is due (see the latest system note). Use
get_account_summary, then end_conversation with a short, friendly check-in:
what they hold, and a reminder that they can change their payments or get in
touch at any time.
"""

PRODUCT_IDS = [p["id"] for p in PRODUCTS]


def function(name: str, description: str, properties: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "strict": True,  # the model's arguments must match this schema
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


TOOL_SCHEMAS = [
    # Phase 1: explore
    function("ask_customer", "Ask the customer one clarifying question.", {
        "question": {"type": "string"},
    }),
    function("search_products", "Find products matching the customer's needs.", {
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "horizon_years": {"type": "integer"},
        "needs_access": {"type": "boolean", "description": "May need the money at short notice"},
    }),
    function("get_product_details", "Get the full description, risk and fees of a product.", {
        "product_id": {"type": "string", "enum": PRODUCT_IDS},
    }),
    function("check_isa_allowance", "Check how much of this year's ISA allowance is left.", {}),
    function("present_options", "Present one to three options to the customer. Ends the conversation.", {
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "enum": PRODUCT_IDS},
                    "name": {"type": "string"},
                },
                "required": ["product_id", "name"],
                "additionalProperties": False,
            },
        },
        "explanation": {"type": "string", "description": "Trade-offs and risks, in plain English"},
    }),
    # Phase 2: get started, and the later review
    function("get_account_summary", "What the customer holds, its risk and its fees.", {
        "product_id": {"type": "string", "enum": PRODUCT_IDS},
    }),
    function("suggest_contribution_plan", "Show what a payment plan looks like over a year.", {
        "product_id": {"type": "string", "enum": PRODUCT_IDS},
        "amount": {"type": "number", "description": "Pounds per payment"},
        "frequency": {"type": "string", "enum": ["one-off", "monthly"]},
    }),
    function("schedule_review", "Book a check-in with the customer a number of months from now.", {
        "months": {"type": "integer", "description": "1 to 24"},
    }),
    function("set_maturity_instruction", "Record what happens when a fixed-term product ends.", {
        "option": {"type": "string", "enum": ["pay out to bank account",
                                              "move to Easy Access Cash ISA", "decide later"]},
    }),
    function("send_guide", "Send the customer a short plain-English guide.", {
        "topic": {"type": "string", "enum": ["what happens when markets fall",
                                             "how fees affect your returns", "how ISAs work"]},
    }),
    function("end_conversation", "Send a closing message. Ends the conversation.", {
        "message": {"type": "string"},
    }),
]
SCHEMAS = {t["function"]["name"]: t for t in TOOL_SCHEMAS}

PHASES = {
    "explore": {
        "prompt": EXPLORE_PROMPT,
        "tools": ["ask_customer", "search_products", "get_product_details",
                  "check_isa_allowance", "present_options"],
        "last_tool": "present_options",
    },
    "get_started": {
        "prompt": GET_STARTED_PROMPT,
        "tools": ["ask_customer", "get_account_summary", "suggest_contribution_plan",
                  "check_isa_allowance", "set_maturity_instruction", "send_guide",
                  "schedule_review", "end_conversation"],
        "last_tool": "end_conversation",
    },
    "review": {
        "prompt": REVIEW_PROMPT,
        "tools": ["get_account_summary", "end_conversation"],
        "last_tool": "end_conversation",
    },
}


def check_tool_call(phase: str, tool: str, args: dict, history: list[dict]) -> str | None:
    """Rules the model cannot break. Returns an error to send back, or None."""
    if tool not in PHASES[phase]["tools"]:
        return f"Tool not available in this phase: {tool}"
    if tool == "present_options":
        searches = [h["result"] for h in history
                    if h["role"] == "tool" and h["tool"] == "search_products"]
        found = {p["id"] for result in searches for p in result}
        if not 1 <= len(args["options"]) <= 3:
            return "Present between one and three options."
        if any(o["product_id"] not in found for o in args["options"]):
            return "Only present products returned by search_products."
    if tool == "end_conversation" and args["message"].rstrip().endswith("?"):
        return "The customer cannot reply to a closing message. Use ask_customer first."
    if tool == "schedule_review" and not 1 <= args["months"] <= 24:
        return "A review must be between 1 and 24 months away."
    if tool in ("suggest_contribution_plan", "set_maturity_instruction"):
        summaries = [h["result"] for h in history
                     if h["role"] == "tool" and h["tool"] == "get_account_summary"]
        if not summaries:
            return "Check the account summary first."
        if tool == "suggest_contribution_plan" and not summaries[-1]["allows_top_ups"]:
            return "This product does not accept further payments."
        said = " ".join(h["text"] for h in history if h["role"] == "customer")
        figures = {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", said)}
        if tool == "suggest_contribution_plan" and int(args["amount"]) not in figures:
            return "Ask the customer how much they want to pay in. Do not assume an amount."
        if tool == "set_maturity_instruction" and summaries[-1]["allows_top_ups"]:
            return "Maturity instructions are only for fixed-term products."
    return None


async def openai_decide(phase: str, history: list[dict], final_turn: bool) -> dict:
    config = PHASES[phase]
    response = await AsyncOpenAI().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
        messages=to_openai_messages(config["prompt"], history),
        tools=[SCHEMAS[name] for name in config["tools"]],
        parallel_tool_calls=False,
        # Always call a tool; on the last turn, it must be the one that ends the phase.
        tool_choice={"type": "function", "function": {"name": config["last_tool"]}}
        if final_turn else "required",
    )
    call = response.choices[0].message.tool_calls[0].function
    return {"tool": call.name, "args": json.loads(call.arguments)}


def to_openai_messages(prompt: str, history: list[dict]) -> list[dict]:
    """Translate the Workflow's history into OpenAI's chat format."""
    messages = [{"role": "system", "content": prompt}]
    call_id = None
    for i, h in enumerate(history):
        if h["role"] == "note":
            messages.append({"role": "system", "content": h["text"]})
        elif h["role"] == "customer":
            messages.append({"role": "user", "content": h["text"]})
        elif h["role"] == "agent":
            call_id = f"call_{i}"
            messages.append({"role": "assistant", "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": h["tool"], "arguments": json.dumps(h["args"])},
            }]})
        elif h["role"] == "tool":
            messages.append({"role": "tool", "tool_call_id": call_id,
                             "content": json.dumps(h["result"])})
    return messages
