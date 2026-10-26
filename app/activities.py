import os

from temporalio import activity

from app.agent import openai_decide
from app.fake_model import fake_decide
from app.models import KycInput
from app.products import PRODUCTS

RISK_ORDER = ["low", "medium", "high"]

# --- The agent's "brain": one model call that picks the next tool. ---


@activity.defn
async def decide_next_step(phase: str, history: list[dict], final_turn: bool) -> dict:
    if os.environ.get("USE_FAKE_MODEL") == "1":
        return fake_decide(phase, history, final_turn)
    return await openai_decide(phase, history, final_turn)


# --- Agent tools. The agent can look and talk, but cannot change anything. ---


@activity.defn
async def ask_customer(args: dict) -> str:
    # The question reaches the customer through the Workflow's reply; a real
    # system might also push it to a chat channel or app here.
    return "Question sent"


@activity.defn
async def present_options(args: dict) -> str:
    return f"Presented {len(args['options'])} options"


@activity.defn
async def search_products(args: dict) -> list[dict]:
    max_risk = RISK_ORDER.index(args["risk_level"])
    matches = [
        p for p in PRODUCTS
        if RISK_ORDER.index(p["risk"]) <= max_risk
        and p["min_years"] <= args["horizon_years"]
        and (p["easy_access"] or not args["needs_access"])
    ]
    matches.sort(key=lambda p: (RISK_ORDER.index(p["risk"]), p["min_years"]), reverse=True)
    return [{"id": p["id"], "name": p["name"], "isa": p["isa"]} for p in matches[:3]]


@activity.defn
async def get_product_details(args: dict) -> dict:
    return next(p for p in PRODUCTS if p["id"] == args["product_id"])


@activity.defn
async def check_isa_allowance(args: dict) -> dict:
    return {"annual_allowance": 20_000, "used_this_tax_year": 4_000, "remaining": 16_000}


@activity.defn
async def get_account_summary(args: dict) -> dict:
    product = next(p for p in PRODUCTS if p["id"] == args["product_id"])
    return {"product": product["name"], "status": "open",
            "risk": product["risk"], "fees": product["fees"]}


@activity.defn
async def suggest_contribution_plan(args: dict) -> dict:
    amount, monthly = args["amount"], args["frequency"] == "monthly"
    return {
        "amount": amount,
        "frequency": args["frequency"],
        "total_first_year": amount * 12 if monthly else amount,
        "note": "Regular payments spread your buying over time, which smooths out ups and downs."
        if monthly else
        "A one-off payment is invested straight away, so it is exposed to rises and falls straight away.",
    }


@activity.defn
async def schedule_review(args: dict) -> str:
    # The Workflow holds the review as a durable timer; this just confirms it.
    return f"Review booked in {args['months']} months"


@activity.defn
async def end_conversation(args: dict) -> str:
    return "Message sent"


# --- KYC steps. Stubbed: a real system would call identity, address and ---
# --- sanctions providers here.                                           ---


@activity.defn
async def verify_identity(kyc: KycInput) -> str:
    return f"Identity verified for {kyc.customer.name}"


@activity.defn
async def check_proof_of_address(kyc: KycInput, document: str) -> str:
    return f"Proof of address accepted: {document}"


@activity.defn
async def screen_sanctions(kyc: KycInput) -> dict:
    # Mock: common surnames give a possible match, as real screening often does.
    if "smith" in kyc.customer.name.lower():
        return {"possible_match": True,
                "summary": f"Possible sanctions match for {kyc.customer.name}: sent for review"}
    return {"possible_match": False, "summary": f"No sanctions match for {kyc.customer.name}"}


@activity.defn
async def record_consent(kyc: KycInput, terms_version: str, typed: str) -> str:
    return f'{kyc.customer.name} agreed to terms {terms_version} for {kyc.product}: "{typed}"'


@activity.defn
async def open_account(kyc: KycInput) -> str:
    return f"Account opened: {kyc.product} for {kyc.customer.name}"
