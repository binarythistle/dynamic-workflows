# Dynamic Workflows demo

Companion code for the Temporal "Dynamic Workflows" video. The path is
dynamic; the guarantees are not. An agent explores investment options with
the customer, a fixed KYC child Workflow opens the account, then the agent
helps them get started, all recorded in one Temporal history.

Demo only: made-up products, and general guidance rather than financial
advice (UK wording).

- `docs/demo-script.md`: what to type for each take, and what to show
- `docs/build-plan.md`: how the project was built, iteration by iteration

## Run

```
cp .env.example .env                              # then add your OpenAI key
temporal server start-dev --db-filename demo.db   # terminal 1 (UI: http://localhost:8233)
uv run python -m app.worker                       # terminal 2
uv run python -m app.chat "Customer A"            # terminal 3: chat with the agent
```

During KYC the chat asks for proof of address and consent. Other inputs come
from separate terminals, as they would from other people or systems:

```
uv run python -m app.upload customer-a utility-bill.pdf   # a document sent later
uv run python -m app.review alex-smith approve            # compliance reviewer (or decline)
```

Any name containing "Smith" gets a possible sanctions match and waits for review.

Set `USE_FAKE_MODEL=1` in `.env` to run without OpenAI (restart the worker).

## Code map

| File | What it holds |
|---|---|
| `app/workflows.py` | `InvestmentSessionWorkflow` (agent loop, handoff, timer) and `KycWorkflow` (fixed steps) |
| `app/agent.py` | Prompts, tool schemas, phases, the rules the model cannot break, the OpenAI call |
| `app/activities.py` | The model call and every tool and KYC step (all mocked) |
| `app/fake_model.py` | Rule-based stand-in for the model |
| `app/products.py` | The made-up product catalogue |
| `app/chat.py`, `upload.py`, `review.py` | The customer, a late document, a compliance reviewer |

## Durability demo
1. Start a chat and press Enter at the proof-of-address prompt (send it later).
2. Stop the worker (Ctrl+C). The KYC Workflow keeps waiting on the server.
3. Start the worker again, then send the document with `app.upload`.
4. KYC carries on from where it stopped: identity is not checked again.
   After a restart, give it a few seconds to pick up.
