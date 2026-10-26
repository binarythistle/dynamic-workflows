import asyncio
import sys

from temporalio.client import Client, WorkflowHandle, WorkflowUpdateFailedError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCError

from app.models import Customer, Turn
from app.workflows import TASK_QUEUE, TERMS, InvestmentSessionWorkflow, KycWorkflow


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
            elif turn.expecting == "choice":
                # The handoff: the customer chooses; the agent cannot.
                choice = int(input("Which option would you like? (number): "))
                turn = await session.execute_update(InvestmentSessionWorkflow.accept_option, choice)
            elif turn.expecting == "kyc":
                await kyc_steps(client.get_workflow_handle(f"kyc-{customer.customer_id}"), customer)
                turn = await session.execute_update(InvestmentSessionWorkflow.continue_chat)
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


async def kyc_steps(kyc: WorkflowHandle, customer: Customer) -> None:
    """Follow the fixed KYC Workflow, prompting the customer when it needs them."""
    print("\nKYC: Starting account opening and KYC checks.\n")
    seen = set()
    while True:
        try:
            stage = await kyc.query(KycWorkflow.current_stage)
        except RPCError:
            await asyncio.sleep(1)  # no worker running right now; keep waiting
            continue
        if stage in ("done", "declined"):
            return
        if stage not in seen:
            seen.add(stage)
            if stage == "proof of address":
                document = input("KYC: Upload proof of address (type a file name), "
                                 "or press Enter to send it later: ").strip()
                if document:
                    await kyc.signal(KycWorkflow.document_uploaded, document)
                else:
                    print("KYC: Waiting for your document. Send it later with:\n"
                          f"       uv run python -m app.upload {customer.customer_id} <file>\n")
            elif stage == "compliance review":
                print("KYC: Your application needs a quick check by our compliance team.\n"
                      "     Reviewer: uv run python -m app.review "
                      f"{customer.customer_id} approve|decline\n")
            elif stage == "consent":
                await give_consent(kyc)
        await asyncio.sleep(0.5)


async def give_consent(kyc: WorkflowHandle) -> None:
    print(f"\n{TERMS}\n")
    while True:
        typed = input('KYC: Type "I agree" to accept these terms: ')
        try:
            await kyc.execute_update(KycWorkflow.give_consent, typed)
            return
        except WorkflowUpdateFailedError as err:
            print(err.cause.message)


if __name__ == "__main__":
    asyncio.run(main())
