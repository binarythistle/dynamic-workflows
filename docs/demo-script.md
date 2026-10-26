# Demo crib sheet

What to type for each customer, and what to point at in the Temporal UI.
The agent's questions vary run to run, so answer whatever it asks in the
spirit of the customer; the lines below are the ones that steer the path.

## Setup (before recording)

```
temporal server start-dev --db-filename demo.db   # terminal 1, UI at http://localhost:8233
uv run python -m app.worker                       # terminal 2
uv run python -m app.chat "<name>"                # terminal 3, one per customer
                                                  # terminal 4: app.upload / app.review
```

- Real model: `USE_FAKE_MODEL=0` in `.env`. Fallback if the API misbehaves:
  `USE_FAKE_MODEL=1`, then restart the worker.
- A full take is about 45 seconds of machine time plus your typing.
- Re-running a name replaces that customer's previous session (easy retakes).

## Take 1: Customer A, the hourglass end to end

| When the agent asks about | Type |
|---|---|
| Opening | `Hi, I have £10,000 I'd like to invest` |
| Purpose / horizon | `It's for retirement, in about 15 years` |
| Ups and downs | `I'd be fine, I can ride them out` |
| Choice | `1` (Global Shares Index Fund) |
| Proof of address | `utility-bill.pdf` |
| Terms | `I agree` |
| One-off or monthly | `Monthly please` → `£200 a month` |
| Review | `Yes please` |

Point at: the agent's path (questions, search, details) at the top of
`session-customer-a`; the child Workflow `kyc-customer-a`; the
contribution plan and review after it; the timer "Wait 12 months for the
customer's review" firing after 24 seconds, then the agent coming back.

## Take 2: Customer B, same bridge, different road

| When the agent asks about | Type |
|---|---|
| Opening | `I've got £8,000 saved for a house deposit` |
| Horizon | `About 2 years` |
| Access | `I might need it at short notice, and I'd like it tax-free` |
| Choice | the Easy Access Cash ISA |
| Proof of address / terms | `council-tax-bill.pdf` / `I agree` |
| One-off or monthly | `Monthly, £1,500 a month` |

Point at: the ISA allowance check in phase 1; `kyc-customer-b` beside
`kyc-customer-a`, identical steps; after KYC, the code-enforced warning that
£18,000 a year is over the £16,000 remaining allowance.

Line for camera: the model once said £18,000 "fits" within £16,000. Exact
rules live in code; the tool returns the warning and the model passes it on.

## Take 3: Customer C, a path with no payment questions at all

| When the agent asks about | Type |
|---|---|
| Opening / horizon | `I've got £8,000 for a house deposit, in about 2 years` |
| Access | `It can be locked away, I won't need it before then` |
| Choice | the 2-Year Fixed Saver |
| Proof of address / terms | `bank-statement.pdf` / `I agree` |
| End of term | `Pay it out to my bank` |

Point at: after KYC, no contribution plan; the agent asks about the end of
the term instead, because the product cannot take more payments.

## Take 4: Alex Smith, durability and the human in the loop

| Step | Do |
|---|---|
| Chat | `uv run python -m app.chat "Alex Smith"`, any short conversation, pick any option |
| Proof of address | Press **Enter** (send it later) |
| Terminal 2 | **Ctrl+C the worker.** Show `kyc-alex-smith` in the UI, still waiting |
| Terminal 2 | Start the worker again; wait 5 to 10 seconds |
| Terminal 4 | `uv run python -m app.upload alex-smith council-tax-bill.pdf` |
| Chat | "needs a quick check by our compliance team" appears |
| Terminal 4 | `uv run python -m app.review alex-smith approve` (only after that line) |
| Terms | `I agree` |

Point at: in `kyc-alex-smith`, identity was checked once, before the crash,
and not again; the compliance branch, taken by a rule written in advance
("Smith" gives a possible sanctions match), not by the agent.

Variation: `decline` instead of `approve` ends politely without an account.

## Lines to keep precise

- Durable execution guarantees every step is recorded, retried and
  resumable. It does not guarantee the agent chose well; evals and guardrails
  do that.
- The agent gives general guidance, not a personal recommendation. This is UK
  wording; rules differ in other jurisdictions.
- Rejected tool calls (wrong phase, unsearched product, assumed amount) show
  in the history: the agent chooses, code constrains.
