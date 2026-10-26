import asyncio
import sys

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from app.models import Customer
from app.workflows import TASK_QUEUE, InvestmentSessionWorkflow


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "Customer A"
    customer = Customer(name.lower().replace(" ", "-"), name)

    client = await Client.connect("localhost:7233")
    session = await client.start_workflow(
        InvestmentSessionWorkflow.run,
        customer,
        id=f"session-{customer.customer_id}",
        task_queue=TASK_QUEUE,
        id_conflict_policy=WorkflowIDConflictPolicy.TERMINATE_EXISTING,  # easy retakes
    )
    print("Tell the agent what you'd like to do with your money.\n")

    while True:
        text = input(f"{name}: ")
        reply = await session.execute_update(InvestmentSessionWorkflow.customer_says, text)
        print(f"\nAgent: {reply.text}\n")
        if reply.finished:
            break


if __name__ == "__main__":
    asyncio.run(main())
