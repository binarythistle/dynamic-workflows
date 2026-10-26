from temporalio import activity

from app.models import KycInput

# KYC steps. Stubbed: a real system would call identity, address and
# sanctions providers here. Each one is an Activity, so it is retried
# on failure and recorded in the Workflow history.


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
