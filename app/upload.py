"""The customer sends proof of address later, e.g. hours or days after applying."""

import asyncio
import sys

from temporalio.client import Client

from app.workflows import KycWorkflow


async def main() -> None:
    customer_id, file_name = sys.argv[1], sys.argv[2]
    client = await Client.connect("localhost:7233")
    kyc = client.get_workflow_handle(f"kyc-{customer_id}")
    await kyc.signal(KycWorkflow.document_uploaded, file_name)
    print(f"Sent {file_name} to kyc-{customer_id}")


if __name__ == "__main__":
    asyncio.run(main())
