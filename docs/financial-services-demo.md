# Financial services demo: investment agent + KYC

Kept as an alternative. A livelier football version with the same concept is
in docs/transfer-deadline-demo.md.

## Scenario (proposed by presenter)
A person asks for investment options. An agent explores and finds a suitable
investment vehicle. When the person accepts one, a fixed KYC process runs.
Verdict from review: this is a textbook hybrid and matches the product owner's
home equity loan example. It maps cleanly to the toy table (KYC is the bridge).

## Concept mapping
| Demo element | Concept |
|---|---|
| Customer asks, agent searches and compares options | Model chooses the path at runtime (tools, order, number of questions) |
| Customer accepts an option | The handoff point |
| KYC / account-opening process | Fixed steps: same checks, same order, every customer |
| Customer A vs B: different conversations, identical KYC | "Different on the way in, identical on the bridge" |

## Suggested demo shape
1. Customer A asks about investing a lump sum. The agent asks a few questions
   and compares two or three options.
2. Customer A accepts one; the fixed KYC flow starts.
3. Customer B has a different conversation: different questions, options.
4. Customer B accepts; the identical KYC flow runs. Show the two histories
   side by side: different at the start, identical in the middle.

Make KYC visibly rigid with a short labelled checklist, for example:
identity verification, proof of address, sanctions screening, consent to
terms. Keep it short enough to read at a glance.

## Tightening points
1. Order of operations. In real financial services, KYC and suitability checks
   often happen before a firm recommends or opens anything, not only after
   acceptance. "Explore, accept, then onboard with KYC" is a reasonable
   teaching simplification, but expect finance-literate viewers to notice.
   Mitigate by calling the fixed part "account opening and KYC" and having the
   agent give general options and guidance rather than a regulated personal
   recommendation. Check the advice vs guidance distinction with compliance
   (in the UK, the FCA draws this line). This is not legal or compliance advice.
2. Do not imply unsupervised regulated advice. The agent narrows options,
   explains trade-offs and flags risks; the customer makes the final choice.
3. Make the fixed section visibly fixed (see checklist above).

## Where Temporal's value shows
KYC has natural waiting and approval points: documents arrive hours or days
later, and a human compliance reviewer may need to approve an edge case.
That shows why the fixed part needs durability and a human-in-the-loop step
(Signals/Updates), and gives a concrete place to show the recorded history of
every step, both the agent's turns (Activities) and the KYC checks (child
Workflow).

## Evidence to lean on for the "why fixed" argument
- Reg Z section 1026.40 (US HELOC disclosures) prescribes content, grouping,
  order and timing: "clearly and conspicuously", grouped and segregated,
  certain disclosures precede others, a named brochure, a worked example based
  on a $10,000 balance, no non-refundable fee until three business days after
  receipt. It is the sourced example behind the product owner's loan story.
- CFPB 2023 "Chatbots in consumer finance" spotlight: being wrong about legally
  required information may violate obligations; policy commentary, not a rule.
- Moffatt v. Air Canada (2024 BCCRT 149): the airline was held liable for its
  chatbot's invented refund policy.
- tau-bench (arXiv 2406.12045): pass^k reliability; GPT-4o about 61% pass^1 on
  tau-retail falling to about 25% at pass^8.
- EU AI Act Annex III: AI used to evaluate creditworthiness is high-risk;
  verify application dates on EUR-Lex.
Note: the KYC and claims-style flows are illustrative reference architectures,
not sourced case studies.
