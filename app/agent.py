"""The agent: what it may do, its limits, and the call to the model.

The model only ever picks the next tool. The Workflow runs that tool, records
it, and enforces the rules below. That is "agent chooses, code constrains".
"""

import json
import os

from openai import AsyncOpenAI

from app.products import PRODUCTS

# Guardrail: on the last turn the agent must present options, so every
# conversation reaches the handoff.
MAX_TURNS = 12

DISCLAIMER = (
    "This is general guidance, not personal advice. The value of investments "
    "can go down as well as up, and you may get back less than you put in."
)

SYSTEM_PROMPT = """\
You are a guidance assistant for a UK investment firm. This is a demo and the
products are made up.

You give general guidance, not a personal recommendation or regulated financial
advice. Your job is to help the customer understand which of the firm's
products may be worth considering. The customer makes the choice.

- Ask short clarifying questions with ask_customer, one at a time: what the
  money is for, how long it can be invested, how they feel about falls in
  value, and whether they may need access to it. Ask only what you need.
- Use search_products and get_product_details to find and understand options.
  Only check the ISA allowance if an ISA is being considered.
- Finish with present_options: one to three products from your search results,
  with a plain-English explanation of the trade-offs and risks of each. Do not
  say which one they should choose.
- Never promise returns. Keep every message to one to three sentences.
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
]


def check_tool_call(tool: str, args: dict, history: list[dict]) -> str | None:
    """Rules the model cannot break. Returns an error to send back, or None."""
    if tool not in [t["function"]["name"] for t in TOOL_SCHEMAS]:
        return f"Unknown tool: {tool}"
    if tool == "present_options":
        searches = [h["result"] for h in history
                    if h["role"] == "tool" and h["tool"] == "search_products"]
        found = {p["id"] for result in searches for p in result}
        if not 1 <= len(args["options"]) <= 3:
            return "Present between one and three options."
        if any(o["product_id"] not in found for o in args["options"]):
            return "Only present products returned by search_products."
    return None


async def openai_decide(history: list[dict], final_turn: bool) -> dict:
    response = await AsyncOpenAI().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
        messages=to_openai_messages(history),
        tools=TOOL_SCHEMAS,
        parallel_tool_calls=False,
        # Always call a tool; on the last turn, it must be present_options.
        tool_choice={"type": "function", "function": {"name": "present_options"}}
        if final_turn else "required",
    )
    call = response.choices[0].message.tool_calls[0].function
    return {"tool": call.name, "args": json.loads(call.arguments)}


def to_openai_messages(history: list[dict]) -> list[dict]:
    """Translate the Workflow's history into OpenAI's chat format."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    call_id = None
    for i, h in enumerate(history):
        if h["role"] == "customer":
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
