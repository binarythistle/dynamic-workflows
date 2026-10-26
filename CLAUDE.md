# Dynamic Workflows video (Temporal AI series, ~13 min)

## Goal
Explain "dynamic workflows" from vendor-neutral AI principles in a video, 
with a supporting code project, then show
where Temporal fits. Not about Temporal's existing Dynamic Workflow SDK
feature (that is about names, not decisions).

## Core idea
The path is dynamic. The guarantees are not. Agent chooses the path;
fixed steps guarantee the parts that must be exact; a durable runtime
records every step.

## Decisions so far
- Opening: toy-car tabletop cold open (hourglass road, bridge in the
  middle, run twice by different routes), ending on the hook question.
  Then Temporal ident, then welcome. Animation can move to the
  definition section.
- Hook: "Can you let an AI choose its own route, and still guarantee
  exactly what it does?"
- Demo domain: financial services. Agent explores investment options
  (open path), customer accepts, fixed KYC/account-opening flow.
- Keep the guarantee claim precise: durability and recording, not
  correctness of the agent's choices.
- Code should be Python
- LLM: OpenAI (plain `openai` SDK, hand-written tool loop)
- Customer acceptance: Temporal Update from the CLI
- Wording: UK (FCA guidance, not advice); note other jurisdictions differ
- Build plan and iterations: @docs/build-plan.md

## Files
- @docs/research-report.md (read when you need evidence or sources)
- @docs/financial-services-demo.md - concept for this code project

## Callouts
- Regulatory wording of the demo (advice vs guidance): this is just a 
  demo but workding should be there