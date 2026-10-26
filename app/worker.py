import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app import activities
from app.workflows import TASK_QUEUE, KycWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[KycWorkflow],
        activities=[
            activities.verify_identity,
            activities.check_proof_of_address,
            activities.screen_sanctions,
            activities.record_consent,
            activities.open_account,
        ],
    )
    print(f"Worker listening on '{TASK_QUEUE}'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
