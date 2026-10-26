import asyncio
import sys

from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.common import WorkflowIDConflictPolicy

from app.models import Customer, Turn
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

    turn = Turn([], "message")
    while turn.expecting != "done":
        try:
            if turn.expecting == "message":
                text = input(f"{name}: ")
                turn = await session.execute_update(InvestmentSessionWorkflow.customer_says, text)
            else:
                # The handoff: the customer chooses; the agent cannot.
                choice = int(input("Which option would you like? (number): "))
                turn = await session.execute_update(InvestmentSessionWorkflow.accept_option, choice)
        except ValueError:
            print("Please type a number.")
            continue
        except WorkflowUpdateFailedError as err:
            print(err.cause.message)
            continue
        for message in turn.messages:
            print(f"\n{message.sender}: {message.text}\n")

    # If a review was booked, the Workflow is now sleeping on a durable timer.
    review = await session.result()
    if review:
        print(f"Agent: {review}\n")


if __name__ == "__main__":
    asyncio.run(main())
