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
