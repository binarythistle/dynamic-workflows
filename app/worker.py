import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.activities import say_hello
from app.workflows import TASK_QUEUE, HelloWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HelloWorkflow],
        activities=[say_hello],
    )
    print(f"Worker listening on '{TASK_QUEUE}'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
