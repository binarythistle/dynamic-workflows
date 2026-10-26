from temporalio import activity

from app.agent import fake_decide
from app.models import KycInput
from app.products import PRODUCTS

RISK_ORDER = ["low", "medium", "high"]

# --- The agent's "brain". Iteration 4 swaps the fake model for a real LLM. ---


@activity.defn
async def decide_next_step(history: list[dict], final_turn: bool) -> dict:
    return fake_decide(history, final_turn)


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


# --- KYC steps. Stubbed: a real system would call identity, address and ---
# --- sanctions providers here.                                           ---


@activity.defn
async def verify_identity(kyc: KycInput) -> str:
    return f"Identity verified for {kyc.customer.name}"


@activity.defn
async def check_proof_of_address(kyc: KycInput) -> str:
    return f"Proof of address accepted for {kyc.customer.name}"


@activity.defn
async def screen_sanctions(kyc: KycInput) -> str:
    return f"No sanctions match for {kyc.customer.name}"


@activity.defn
async def record_consent(kyc: KycInput) -> str:
    return f"{kyc.customer.name} consented to the terms for {kyc.product}"


@activity.defn
async def open_account(kyc: KycInput) -> str:
    return f"Account opened: {kyc.product} for {kyc.customer.name}"
