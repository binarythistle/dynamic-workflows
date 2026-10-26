import asyncio

from temporalio.client import Client

from app.models import Customer, KycInput
from app.workflows import TASK_QUEUE, KycWorkflow

# Iteration 1: run KYC on its own for two customers. Later the agent
# conversation decides the product; here it is fixed.
RUNS = [
    KycInput(Customer("customer-a", "Customer A"), "Global Index Fund"),
    KycInput(Customer("customer-b", "Customer B"), "Cash ISA"),
]


async def main() -> None:
    client = await Client.connect("localhost:7233")
    for kyc in RUNS:
        steps = await client.execute_workflow(
            KycWorkflow.run,
            kyc,
            id=f"kyc-{kyc.customer.customer_id}",
            task_queue=TASK_QUEUE,
        )
        print(f"\n{kyc.customer.name}:")
        for step in steps:
            print(f"  - {step}")


if __name__ == "__main__":
    asyncio.run(main())
