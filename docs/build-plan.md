# Build plan: investment agent + fixed KYC (Python, Temporal)

## Guiding rules
- Simplest code that shows the idea on screen. Every file should be
  readable in a single shot on camera.
- The **Temporal Web UI event history is the main visual**. A plain CLI is
  the only "front end" until we decide we need more.
- One concept per iteration. Each one ends runnable, with a short review
  before the next starts.
- Agent output is **general guidance, not a personal recommendation**. The
  customer picks; the agent narrows and explains.

## Target shape (what the finished code proves)
```
InvestmentSessionWorkflow            <- the path is dynamic
  loop: llm_decide (Activity) -> tool call (Activity) -> ...
  wait for customer acceptance (Update)
  └─ KycWorkflow (child)             <- the guarantees are not
       verify_identity -> proof_of_address (wait for doc)
       -> sanctions_screen -> [compliance review if flagged] -> consent -> open_account
```
- The agent loop lives in the Workflow; each model call and each tool call
  is an Activity. That is why the history records every decision, and why
  replay is deterministic even though the model is not.
- KYC is a separate child Workflow with hard-coded order. Same steps, same
  order, every customer.

Planned layout (small, flat):
```
app/
  workflows.py     # InvestmentSessionWorkflow, KycWorkflow
  activities.py    # llm_decide, tools, KYC steps (stubbed)
  agent.py         # system prompt, tool schemas, guardrail limits
  worker.py
  starter.py       # run customer A / B from the CLI
```

## Iterations

| # | Goal | Done when | Video beat it supports |
|---|---|---|---|
| 0 | Skeleton: `uv` project, `temporalio`, dev server, worker | Hello Workflow visible in UI | — |
| 1 | **Fixed KYC child Workflow** alone, stubbed Activities | Two runs give identical histories | "The bridge": fixed steps |
| 2 | **Agent loop with a fake (scripted) model** | Customer A and B take different tool paths; each step is an Activity in history | "The path is dynamic" |
| 3 | **Join them**: acceptance via Update, then start KYC child | One history: varied start, identical middle | Core hybrid (A vs B side by side) |
| 4 | **Swap in a real LLM** behind the same `llm_decide` Activity; add guardrails (max turns, tool allowlist, schema for the final proposal) | Real conversation, same shape of history | "Agent chooses, code constrains" |
| 5 | **Durability beats**: proof-of-address waits on a Signal (doc arrives later); compliance review on a flagged customer; kill the worker mid-KYC and resume | Resume with no repeated steps | "Durable runtime records every step" |
| 6 | **Demo polish**: seeded customers A/B, readable Activity names, README run script, guidance/disclaimer wording reviewed | Recordable end to end in < 2 min | Recording |

Why this order: the fixed part comes first because it is the easy,
certain part and it fixes the vocabulary. The scripted model in step 2 lets
us get the loop and history right without API keys or nondeterministic
takes. The real LLM comes in only after the structure is settled.

## Deliberately out of scope
- Web UI, real KYC/sanctions providers, a database, auth.
- Model-written orchestration (L5). Mention in the video, don't build it.
- Temporal's Dynamic Workflow SDK feature (names, not decisions).
- Frameworks (LangGraph, OpenAI Agents SDK). A hand-written loop is
  shorter to show and vendor-neutral.

## Decisions
1. Acceptance: Temporal Update sent from the CLI (iteration 3).
2. LLM provider: OpenAI, via the plain `openai` Python SDK with a
   hand-written tool-calling loop (no Agents SDK). Key from `OPENAI_API_KEY`.
   The `llm_decide` Activity boundary keeps it swappable (iteration 4).
3. Wording: UK. The agent gives guidance, not a personal recommendation
   (FCA advice vs guidance line). On camera, note that rules differ in
   other jurisdictions. Affects prompt and disclaimer text only.
4. Products: 4-5 made-up generic products with clear plain-English
   descriptions (e.g. cash ISA, global index fund, bond fund, balanced
   multi-asset fund). No real named funds.
