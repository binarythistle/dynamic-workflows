# Dynamic Workflows demo

Companion code for the Temporal "Dynamic Workflows" video. See
`docs/build-plan.md` for the iteration plan.

## Run

```
cp .env.example .env                          # then add your OpenAI key
temporal server start-dev                     # terminal 1 (UI: http://localhost:8233)
uv run python -m app.worker                   # terminal 2
uv run python -m app.chat "Customer A"        # terminal 3: chat with the agent
```

During KYC the chat asks for proof of address and consent. Other inputs come
from separate terminals, as they would from other people or systems:

```
uv run python -m app.upload customer-a utility-bill.pdf   # a document sent later
uv run python -m app.review alex-smith approve            # compliance reviewer (or decline)
```

Any name containing "Smith" gets a possible sanctions match and waits for review.

Set `USE_FAKE_MODEL=1` in `.env` to run without OpenAI (restart the worker).

## Durability demo
1. Start a chat and press Enter at the proof-of-address prompt (send it later).
2. Stop the worker (Ctrl+C). The KYC Workflow keeps waiting on the server.
3. Start the worker again, then send the document with `app.upload`.
4. KYC carries on from where it stopped: identity is not checked again.
   After a restart, give it a few seconds to pick up.
