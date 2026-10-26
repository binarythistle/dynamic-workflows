# Dynamic Workflows in AI Systems: A Vendor-Neutral Mental Model

Research report prepared for the Temporal AI video series. Reconstructed from
the original research conversation; wording is paraphrased where it draws on
sources. Verify vendor facts before quoting on camera.

## Summary

A "dynamic workflow" is best defined as a system in which the control flow
(which steps run, in what order, how many, and when to stop) is decided or
written at runtime, by a model or from data, rather than fixed entirely by a
human at design time, and is then carried out by an execution layer that
enforces structure, state and limits.

In practice every production system is a hybrid of model-decided and
code-fixed steps. In 2026 "Dynamic Workflows" also became the branded name for
one point on that spectrum: the model writes orchestration code and a runtime
executes it durably. The Temporal product owner's hybrid narrative is
directionally right and well supported. Its main gap is that it says little
about the "model writes the workflow" form that Anthropic, GitHub and
Cloudflare actually ship under this name.

### TL;DR
- Generic definition: control flow chosen or authored at runtime inside bounds
  that code enforces. Sits between Anthropic's "workflows" (predefined code
  paths) and "agents" (LLMs that direct their own process). Key design
  questions: who decides the next step, who authored the orchestration, and
  what guarantees it runs.
- Vendor usage is overloaded: Anthropic and GitHub mean orchestration programs
  (often model-written) fanning work out to many subagents. Cloudflare means
  durable execution for code loaded at runtime (per tenant or per agent).
  Google ADK 2.0 means code-based control flow instead of static graphs.
  Temporal's existing feature is a catch-all handler for unregistered
  workflow/activity type names: a different concept.
- Why hybrids persist: compounding error, regulation that prescribes exact
  content and order, cost and latency, testability, liability.

## 1. The mental model: three questions

1. Who decides the next step at runtime? Fixed code, a classifier/router, or an
   LLM in a loop.
2. Who authored the orchestration, and when? A human at design time, an LLM at
   runtime (plan or script), or a human codifying what an LLM discovered
   (hardening).
3. What guarantees execution? In-memory process (lost on crash), checkpointing,
   or durable execution with recorded history, retries, timeouts, human gates
   and versioning.

"Dynamic" describes answers to 1 and 2 that move toward runtime and the model.
"Workflow" describes 3: structure, state, and a runtime holding it.

Metaphor (used in the road-trip animation): the agent is the driver, the
workflow is the road network and traffic rules, and the durable runtime is the
odometer and black-box recorder. The recorder guarantees the trip is logged and
resumable. It does not guarantee the driver chose the right road.

## 2. Spectrum of control-flow authority

| Level | Pattern | Who decides control flow | Who authors orchestration | Example |
|---|---|---|---|---|
| L0 | Static workflow | Code | Human, design time | Classic ETL/BPM; KYC document checklist |
| L1 | Workflow with LLM steps (prompt chaining) | Code; LLM only transforms content | Human, design time | Extract fields, validate, summarize |
| L2 | Routed/branching workflow | LLM or classifier picks among prebuilt branches | Human, design time | Support triage into refund/tech/billing flows |
| L3 | Agent-chosen tools (agent loop) | LLM, turn by turn | Human defines tools and limits; model sequences them | ReAct-style assistant; OpenAI Agents SDK loop |
| L4 | Agent-generated plan (orchestrator-workers, plan-and-execute) | LLM writes a plan; an executor runs it | Model at runtime (plan as data) | Research agent decomposes into subtasks |
| L5 | Agent-generated/compiled workflow (code-as-orchestration) | The generated script | Model at runtime (executable code), run by a runtime with limits | Claude Code / Managed Agents dynamic workflows; CodeAct |
| L6 | Hardened (crystallized) workflow | Code, with residual LLM steps | Human or pipeline codifies what the agent discovered | Saved Claude/Copilot workflow; Azure "Type 1" playbook |

Notes:
- Anthropic's patterns map onto L1-L4: prompt chaining (L1), routing (L2),
  parallelization (L1/L2), orchestrator-workers (L4), evaluator-optimizer
  (loops in L1-L3), agents (L3).
- L5 has research support: CodeAct (arXiv 2402.01030) found that letting LLMs
  emit executable Python as actions gave up to 20% higher success than
  alternatives, partly because code natively expresses loops and data flow.
- L6 closes the loop back toward L0/L1. That loop, with promotion and
  demotion, is the lifecycle the product owner describes.
- Real systems nest: an L0 outer process can contain an L3 agent step, which
  can call an L6 hardened sub-workflow. HumanLayer's 12-Factor Agents describes
  production agents as mostly deterministic code with LLM steps at the right
  points.

## 3. How vendors use "Dynamic Workflows"

### Anthropic (Claude Code, GA; Claude Managed Agents, public beta)
- Announced May 28, 2026 for Claude Code. Claude writes an orchestration script
  (JavaScript) that runs many subagents in parallel; a runtime executes it in
  the background. Primitives include agent(), parallel(), pipeline(), phase().
  Schemas validate structured output, runs are resumable, and a run can be saved
  to .claude/workflows/ as a reusable command. Bundled example: /deep-research.
- Managed Agents (Oct 9, 2026, beta): a workflow is a program that runs many
  agents in phases and combines results, executed server-side as a workflow run.
  Secondary reports cite a cap of 1,000 agents per run (unverified).
- Showcase: a port of Bun from Zig to Rust (about 750,000 lines of Rust, eleven
  days from first commit to merge, 99.8% of existing tests passing), driven by a
  fix loop using the build and test suite.
- Caveat: Anthropic warns these can use substantially more tokens than a
  typical session. A secondary report of 66 of 70 planted bugs found versus
  14-27 for single-agent runs could not be verified against a primary page.
- Maps to the generic concept: yes, strongly. L5 with an L6 save path.

### GitHub (Copilot CLI, Copilot app, Copilot SDK; public preview, Oct 1, 2026)
- A dynamic workflow is a program that defines how a task is carried out,
  combining automated steps with the work of one or more agents. Everything is
  defined in code: steps, when to involve agents, how to use results. Agents
  handle parts that need analysis or judgment. Authored by Copilot, by you, or
  shared with you.
- Contrast GitHub draws: in Autopilot, Copilot decides the next steps; in
  /fleet, Copilot decides how to divide the work; in a dynamic workflow the
  workflow author defines steps, conditions and handoffs. The path can still
  change with inputs, and agents may answer differently run to run.
- Controls: caps on concurrent and total agents, active time and AI credits;
  pause/resume at checkpoints; run from CI. Canonical example: incident
  investigation.
- Maps to the generic concept: yes, nearly the product owner's hybrid thesis
  (code fixes the skeleton, agents fill judgment steps). Closer to L6.

### Cloudflare (@cloudflare/dynamic-workflows, open beta, May 1, 2026)
- A small MIT-licensed TypeScript library, built on Dynamic Workers, that lets
  platforms route durable execution to tenant- or agent-provided code on the
  fly. Previously workflow code had to ship with the deployment. Each create()
  can now route to different code, and the engine dispatches back to that same
  code later (seconds to days), with step.sleep, step.waitForEvent and retries
  unchanged.
- Maps to the generic concept: partially. "Dynamic" means dynamically loaded
  code, not model-decided control flow. It is the substrate that makes L5
  durable. Clearest industry statement that agent-generated workflows need
  durable execution.

### Temporal (existing SDK feature)
- Dynamic Workflows/Activities/Signals/Queries/Updates are unnamed handlers
  invoked when no statically defined handler with that name exists. Docs advise
  using them as a fallback. The Java docs note a main use is custom DSL
  interpreters. Determinism rules still apply.
- Maps to the generic concept: no. It is name-based dispatch. Adjacent, since a
  dynamic handler acting as a DSL interpreter is one way to execute an
  LLM-generated plan (L4).

### Other usages
- Google ADK 2.0: graph-based, dynamic (code-based logic with loops and
  decision-based branching, using native Python control flow) and collaborative
  workflows. Here "dynamic" means code-defined, data-dependent control flow
  written by a human.
- LangGraph: conditional edges and the Send API (dynamically creates worker
  nodes); workflows, agents and anything in between; checkpointing.
- OpenAI Agents SDK: names the poles "orchestrating via LLM" vs "orchestrating
  via code" and recommends mixing.
- Microsoft Agent Framework: separates model-driven agents from workflows
  (predefined graphs with checkpointing). Per secondary comparisons only.
- Vercel Workflow DevKit: "use workflow"/"use step" make async TypeScript
  durable; DurableAgent runs agent tool calls as retryable steps.
- Inngest, Restate, DBOS: same durable-execution-for-agents wave; primary docs
  not reviewed.

## 4. Disambiguation from Temporal's existing feature

| | Temporal Dynamic Workflow/Activity (SDK) | "Dynamic workflows" (AI sense) |
|---|---|---|
| Question | What code handles a type name I didn't register? | Who decides or writes the control flow at runtime? |
| Dynamic dimension | Name-based dispatch | Path, step count, ordering, fan-out, authorship |
| Determinism | Must still be deterministic | Model decisions are non-deterministic and must be recorded |
| Typical use | DSL interpreters, generic routers, polyglot fallbacks | Agent loops, model-written orchestration, hybrid flows |

On-screen line: "Temporal's Dynamic Workflow feature is about names. Dynamic
workflows in AI are about decisions."

Bridge: on Temporal the agent's runtime decisions live in Workflow history as
recorded Activity results, so replay stays deterministic even though the model
is not. Executing a model-generated plan (L4/L5) needs either an interpreter
Workflow that walks a structured plan (where the DSL-style dynamic handler is
legitimately useful) or child Workflows and Activities selected by name.
Temporal cannot simply load model-written Workflow code the way Cloudflare's
library loads tenant code. That is a real design difference to state honestly.

## 5. Concrete examples (agent decides vs fixed steps guarantee)

- Finance advisor to home equity line (the product owner's example). Agent:
  discovery, comparing options, suggesting a HELOC, follow-ups. Fixed: the
  application flow. Reg Z section 1026.40 requires clear, conspicuous,
  grouped and segregated disclosures; some precede others; disclosures and the
  named brochure are provided with the application; a worked example is based
  on a $10,000 balance; no non-refundable fee until three business days after
  the consumer receives disclosures and brochure; electronic applications must
  not allow bypassing the disclosures. These are exact, checkable requirements:
  a child workflow with templated text, a consumer acknowledgment gate and a
  hand-back. CFPB's 2023 chatbot spotlight warns that being wrong about legally
  required information may violate obligations (policy commentary, not a rule).
- Customer support (refunds, cancellations). Agent: intent, information
  gathering. Fixed: policy checks and the write action, escalation thresholds.
  Evidence: tau-bench scores final database state against policy;
  Moffatt v. Air Canada (2024 BCCRT 149) held the airline liable for its
  chatbot's invented bereavement-refund policy (CA$812.02 total ordered).
- Coding agents. Agent: decomposition, edits, hypotheses. Fixed: build, tests,
  review gates, merge rules, per-agent worktree isolation. The Bun port is a
  model-authored workflow whose stopping condition is a deterministic oracle
  (tests passing).
- Incident response / AIOps. Agent: novel incident investigation. Fixed: write
  actions behind approval gates; known incidents handled by deterministic
  playbooks. GitHub's flagship example; Azure Networking's "Progressive
  Crystallization" paper.
- Insurance claims. Agent: extracting messy documents, drafting rationale.
  Fixed: coverage rules, fraud-score call, payment authorization, audit record.
  Illustrative, not a sourced case study.
- KYC/onboarding. Agent: unusual documents, clarifications. Fixed: identity
  verification sequence, sanctions screening, record retention, human review of
  edge cases. Illustrative. EU AI Act Annex III treats AI evaluating
  creditworthiness as high-risk; verify application dates on EUR-Lex.

## 6. Why hybrids persist

- Error compounds. tau-bench (Sierra, arXiv 2406.12045) introduced pass^k (all
  k trials succeed): GPT-4o scored about 61% pass^1 on tau-retail and about 35%
  on tau-airline, falling to about 25% at pass^8 on tau-retail. Arithmetic
  backs "99% isn't good enough": 20 independent steps at 99% complete cleanly
  about 82% of the time (0.99^20); 50 steps about 61%.
- Compliance prescribes form, order and timing, not just outcomes.
- Liability attaches to the deployer.
- Cost and latency: OpenAI notes code orchestration is more predictable in
  speed, cost and performance; Anthropic warns dynamic workflows use more
  tokens. In the Azure paper, agent-orchestrated runs cost roughly 10k-50k
  tokens, hybrid 1k-5k, deterministic zero.
- Testability: the same paper's taxonomy reports determinism of about 50% for
  agent-orchestrated, about 90% for hybrid and 100% for deterministic playbooks.
- Auditability: regulated flows need an ordered record of what was said and
  done; durable execution history provides it.
- Simplicity: Anthropic advises adding complexity only when it demonstrably
  improves outcomes.

### Lifecycle evidence (explore, then codify)
Microsoft Azure Networking's "Progressive Crystallization" (arXiv 2607.07052,
single author, single organization, not peer reviewed) promotes recurring
incident handling from agent-orchestrated (Type 3) to hybrid (Type 2) to
deterministic playbooks (Type 1). Promotion criteria are concrete: Type 3 to 2
needs at least 10 successful runs, zero safety violations and at least 90% of
runs producing the same action sequence; Type 2 to 1 needs at least 50 hybrid
runs, at least 99% LLM classification consistency and human review of the
deterministic logic. Automatic demotion on regression exists (a firmware update
broke a parser, the playbook dropped back to hybrid, then was re-promoted).
Reported outcomes: deterministic share rose from zero to 45% over eight months
and per-incident agent cost fell by more than 70% while incident volume
doubled. Use as an illustration, not proof of general magnitudes. Related work:
Agent Workflow Memory (arXiv 2409.07429) induces reusable workflows from agent
trajectories; arXiv 2605.22502 compiles procedures into small fine-tuned
models (cheaper but still probabilistic, not deterministic code).

## 7. Critical assessment of the product owner narrative

Where it aligns: "real systems are hybrids" matches Anthropic, LangChain,
OpenAI, Google ADK 2.0, 12-Factor Agents and GitHub's definition. The reasons
(cost, latency, error tolerance, testability, compliance) are the ones vendors
and researchers cite. The explore-then-codify lifecycle is independently
evidenced. The Temporal mapping is accurate (model calls routed through
Activities; Worker Versioning PINNED vs AUTO_UPGRADE; Signals/Updates for human
approval).

Distinctive, keep: treating the codification step as a deployment problem
(patching and Worker Versioning so new fixed paths ship while old runs finish);
workflow history as the single record of every agent turn.

Gaps:
1. Omits the meaning the market now attaches to the term (model-authored
   orchestration programs, L5/L6).
2. Collapses "agent chooses next step" into "dynamic"; the richer model
   separates who decides from who authors.
3. Does not cover guardrails between agent and fixed steps (output schemas,
   validation, policy checks before tools execute, tool permissions, budgets
   and limits on agents, credits and time).
4. "See which paths win" needs a definition of winning: pass^k, acceptance
   tests, human review, demotion on drift.
5. Honest Temporal constraints: Workflow code must be deterministic, so
   model-generated orchestration must be interpreted; Workflow Reset
   re-executes everything after the reset point, so side effects already taken
   (an application already submitted) must be accounted for.

Risk of mis-framing: "let Temporal guarantee the path" can be read as
guaranteeing the agent chose a correct path. Temporal guarantees the chosen
path is executed durably, recorded, retried and resumable. Correctness of fixed
paths comes from code and tests; correctness of agent choices from evals and
guardrails. Also, using "dynamic" near Temporal invites confusion with the SDK
feature unless disambiguated in the first minute, and framing the topic as a
Temporal feature rather than an industry pattern will limit reach.

Suggested adjustments:
- Thesis: "Let the agent choose the path; let code define the rails; let
  durable execution guarantee every step is recorded, retried and resumable."
  Short: "Agents decide. Code constrains. Durable execution remembers."
- Open with the vendor-neutral spectrum and the three questions, then place
  Anthropic, GitHub, Google and Cloudflare on it; present Temporal as the
  substrate for any point.
- Add a segment on "the agent writes the workflow" (L5) and how it is executed
  durably (plan-as-data run by an interpreter Workflow, steps as Activities and
  child Workflows).
- Add a segment on promotion and demotion criteria, borrowing the Azure numbers
  with caveats.

## 8. Recommendations

1. One-sentence definition: "A dynamic workflow is a workflow whose control
   flow (which steps run, in what order, how many times, and when to stop) is
   decided or written at runtime by a model or by data, while code enforces the
   boundaries and a durable runtime records and guarantees each step."
2. Spine: the spectrum and lifecycle, not any vendor (static, LLM steps,
   routed, agent-chosen tools, agent-generated plan, agent-generated workflow,
   hardened workflow, with arrows for promotion and demotion).
3. Anchor with the HELOC example using real Reg Z requirements; use tau-bench
   pass^k for "99% isn't enough".
4. Disambiguate early: names vs decisions; and the Anthropic/GitHub/Cloudflare
   meanings.
5. Reword "guarantee the path" to separate durability from correctness.
6. Label vendor numbers (Anthropic 66/70, Managed Agents limits) as reported,
   and the Azure results as a single-organization case study.

## Glossary

- Workflow (Anthropic sense): LLMs and tools orchestrated through predefined
  code paths.
- Agent: an LLM that dynamically directs its own process and tool use,
  typically using tools based on environmental feedback in a loop.
- Agent loop: model call, tool call(s), observe, decide, until a stop
  condition or turn limit.
- Prompt chaining / routing / parallelization / orchestrator-workers /
  evaluator-optimizer: Anthropic's canonical workflow patterns.
- Plan-and-execute / generated plan: the model emits a structured plan (data)
  that an executor runs.
- Code-as-action (CodeAct): the model emits executable code as its action.
- Code-as-orchestration / dynamic workflow (Anthropic, GitHub sense): a
  program, often model-written, orchestrating many agents with phases, schemas
  and limits.
- Control flow authority: who or what decides the next step.
- Durable execution: a runtime that persists progress so execution survives
  crashes and long waits and resumes without redoing completed steps.
- Human-in-the-loop: explicit pause points for approval (Temporal:
  Signals/Updates; GitHub: checkpoints).
- Crystallization / hardening / codification: promoting repeatedly validated
  agent behavior into fixed steps, with demotion on regression.
- pass^k: probability an agent succeeds on all k repeated trials.
- Temporal Dynamic Workflow/Activity (SDK): fallback handler for unregistered
  type names. Not the AI concept.
- Worker Versioning / Patching: let new code paths ship while in-flight
  executions continue on prior code.
- Workflow Reset: starts a new execution from a chosen history point; later
  events are re-run.

## Caveats and confidence

- The workflows-vs-agents distinction and the hybrid thesis are established
  (high confidence, broad agreement). "Dynamic workflows" as a term is
  emerging and overloaded (medium confidence on any single definition).
- Several product facts are from previews and betas (GitHub public preview,
  Managed Agents beta, Cloudflare open beta) and may change; some limits come
  from secondary write-ups.
- The crystallization evidence is a single-author case study without a
  controlled comparison.
- Regulatory points: the CFPB spotlight is policy commentary; the HELOC
  brochure is named "What You Should Know About Home Equity Lines of Credit";
  EU AI Act application dates reportedly moved, so verify on EUR-Lex.
- KYC and claims examples are illustrative reference architectures.

## Sources (primary where possible)
- Anthropic, Building Effective Agents (engineering blog, Dec 2024)
- Claude Code docs: workflows (code.claude.com/docs/en/workflows) and
  "Introducing dynamic workflows" (claude.com/blog)
- GitHub Docs: Dynamic workflows (docs.github.com/en/copilot/concepts/agents/dynamic-workflows)
- Cloudflare docs: Dynamic Workflows (developers.cloudflare.com/dynamic-workers/usage/dynamic-workflows/)
  and InfoQ coverage (May 2026)
- Temporal docs: Dynamic handlers; OpenAI Agents SDK integration
  (docs.temporal.io/develop/python/integrations/openai-agents)
- Google ADK 2.0 (adk.dev/2.0) and "Why we built ADK 2.0" (developers.googleblog.com)
- LangGraph docs: Workflows and agents (docs.langchain.com)
- OpenAI Agents SDK: Agent orchestration (openai.github.io/openai-agents-python/multi_agent/)
- Vercel Workflow DevKit announcement
- tau-bench: arXiv 2406.12045
- CodeAct: arXiv 2402.01030
- Agent Workflow Memory: arXiv 2409.07429
- Progressive Crystallization: arXiv 2607.07052
- Compiling agentic workflows into weights: arXiv 2605.22502
- 12-Factor Agents (HumanLayer)
- 12 CFR 1026.40 (eCFR); CFPB, Chatbots in consumer finance (2023)
- Moffatt v. Air Canada, 2024 BCCRT 149 (ABA Business Law Today summary)
- EU AI Act Annex III
