from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.activities import (
        check_proof_of_address,
        open_account,
        record_consent,
        screen_sanctions,
        verify_identity,
    )
    from app.models import KycInput

TASK_QUEUE = "investment-demo"


@workflow.defn
class KycWorkflow:
    """The fixed part. Same checks, same order, every customer."""

    @workflow.run
    async def run(self, kyc: KycInput) -> list[str]:
        timeout = timedelta(seconds=30)
        return [
            await workflow.execute_activity(verify_identity, kyc, start_to_close_timeout=timeout),
            await workflow.execute_activity(check_proof_of_address, kyc, start_to_close_timeout=timeout),
            await workflow.execute_activity(screen_sanctions, kyc, start_to_close_timeout=timeout),
            await workflow.execute_activity(record_consent, kyc, start_to_close_timeout=timeout),
            await workflow.execute_activity(open_account, kyc, start_to_close_timeout=timeout),
        ]
