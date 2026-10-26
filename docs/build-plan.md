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
InvestmentSessionWorkflow
  phase 1, explore                   <- the path is dynamic
  loop: decide_next_step (Activity) -> tool call (Activity) -> ...
        ask_customer = wait for a live typed reply (Update)
  wait for customer acceptance (Update)
  └─ KycWorkflow (child)             <- the guarantees are not
       verify_identity -> proof_of_address (wait for doc)
       -> sanctions_screen -> [compliance review if flagged]
       -> consent (customer agrees to fixed terms text) -> open_account
  phase 2, get started               <- dynamic again
  same agent loop, different prompt and tools
```
This is the hourglass from the cold open: wide, the bridge, wide again.
- The agent loop lives in the Workflow; each model call and each tool call
  is an Activity. That is why the history records every decision, and why
  replay is deterministic even though the model is not.
- `ask_customer` is not an Activity: the Workflow pauses until the customer
  types a reply at the CLI (sent as an Update). The conversation is human
  in the loop and durable from the start.
- KYC is a separate child Workflow with hard-coded order. Same steps, same
  order, every customer. Fixed does not mean linear: the compliance review
  branch is decided by a rule written in advance, not by the agent.
- Phase 2 reuses the phase 1 loop unchanged; only the prompt and tool set
  differ.

Planned layout (small, flat):
```
app/
  workflows.py     # InvestmentSessionWorkflow, KycWorkflow
  activities.py    # decide_next_step, tools, KYC steps (stubbed)
  agent.py         # system prompt, tool schemas, guardrail limits
  worker.py
  starter.py       # run customer A / B from the CLI
```

## Agent tools, phase 1: explore (all read-only, mocked)
| Tool | Purpose |
|---|---|
| `ask_customer(question)` | Clarifying question; reply typed live |
| `search_products(risk_level, horizon, needs_access)` | Filter the made-up catalogue |
| `get_product_details(product_id)` | Description, risk, fees, access |
| `check_isa_allowance(customer_id)` | Remaining £20,000 ISA allowance |
| `present_options(options, explanation)` | Ends the loop; schema-checked handoff |

The agent has no write tools. Only the fixed KYC flow changes anything.
Every session ends at `present_options` (a turn limit forces it), so KYC
is always reached however the conversation goes.

## Agent tools, phase 2: get started (mocked)
| Tool | Purpose |
|---|---|
| `ask_customer(question)` | As phase 1, typed live |
| `get_account_summary()` | Holdings, amount paid in, costs |
| `suggest_contribution_plan(amount, frequency)` | Lump sum vs monthly, as guidance |
| `schedule_review(months)` | Durable timer for a later check-in (months shortened to seconds for the demo) |

Phase 2 is optional: if the video runs long, it can be cut without
affecting anything else.

## Iterations

| # | Goal | Done when | Video beat it supports |
|---|---|---|---|
| 0 | Skeleton: `uv` project, `temporalio`, dev server, worker | Hello Workflow visible in UI | — |
| 1 | **Fixed KYC child Workflow** alone, stubbed Activities | Two runs give identical histories | "The bridge": fixed steps |
| 2 | **Agent loop with a fake rule-based model**, answers typed live at the CLI | Different answers give different tool paths; each step is in history | "The path is dynamic" |
| 3 | **Join them**: acceptance via Update, then start KYC child | One history: varied start, identical middle | Core hybrid (A vs B side by side) |
| 4 | **Swap in a real LLM** behind the same `decide_next_step` Activity; add guardrails (max turns, tool allowlist, schema for the final proposal) | Real conversation, same shape of history | "Agent chooses, code constrains" |
| 5 | **Phase 2, get started**: rerun the agent loop after KYC with the phase 2 prompt and tools; `schedule_review` as a durable timer | A and B diverge again after identical KYC; the review timer fires and the agent resumes | Hourglass: "different again on the far side" |
| 6 | **Durability beats**: proof-of-address waits on a Signal (doc arrives later); compliance review on a flagged customer; consent as real customer input (fixed terms text shown at the CLI, customer types "I agree" via Update, recorded verbatim); kill the worker mid-KYC and resume | Resume with no repeated steps; consent text identical for every customer | "Durable runtime records every step" |
| 7 | **Demo polish**: crib sheet of what to type as customers A/B, readable Activity names, README run script, guidance/disclaimer wording reviewed | Recordable end to end in < 2 min | Recording |

Why this order: the fixed part comes first because it is the easy,
certain part and it fixes the vocabulary. The rule-based fake model in step 2
lets us get the loop, live chat and history right without API keys. The real LLM comes in only after the structure is settled.

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
   The `decide_next_step` Activity boundary keeps it swappable (iteration 4).
3. Wording: UK. The agent gives guidance, not a personal recommendation
   (FCA advice vs guidance line). On camera, note that rules differ in
   other jurisdictions. Affects prompt and disclaimer text only.
4. Products: 4-5 made-up generic products with clear plain-English
   descriptions (e.g. cash ISA, global index fund, bond fund, balanced
   multi-asset fund). No real named funds.
5. Customer answers are typed live at the CLI (resonates more on camera).
