import asyncio
import sys

from temporalio.client import Client

from app.workflows import TASK_QUEUE, HelloWorkflow


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "Customer A"
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        HelloWorkflow.run, name, id=f"hello-{name}", task_queue=TASK_QUEUE
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
