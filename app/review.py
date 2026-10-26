"""A human compliance reviewer approves or declines a flagged application."""

import asyncio
import sys

from temporalio.client import Client

from app.models import ComplianceDecision
from app.workflows import KycWorkflow


async def main() -> None:
    customer_id, verdict = sys.argv[1], sys.argv[2]
    client = await Client.connect("localhost:7233")
    kyc = client.get_workflow_handle(f"kyc-{customer_id}")
    await kyc.signal(
        KycWorkflow.compliance_decision,
        ComplianceDecision(approved=verdict == "approve", reviewer="Compliance team"),
    )
    print(f"Compliance decision for kyc-{customer_id}: {verdict}")


if __name__ == "__main__":
    asyncio.run(main())
