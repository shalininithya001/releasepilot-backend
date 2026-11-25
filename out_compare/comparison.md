# Provider comparison for release R2.4

`*` = that provider could not finish the requirement (not a real decision).

| Provider | Model | Overall | Degraded | Not assessed | Wall time (s) | Tool calls | Tokens |
|---|---|---|---|---|---|---|---|
| gemini | gemini:gemini-3.5-flash | NEEDS_REVIEW | True | 11 | 1712.7 | 32 | 76452 |
| openrouter | openrouter:nvidia/nemotron-3.5-lightning:free | BLOCKED | True | 7 | 1327.9 | 71 | 325940 |
| nvidia | nvidia:mistralai/mistral-large-4-1t-a52b | BLOCKED | True | 2 | 2976.9 | 204 | 482924 |

| Requirement | Title | gemini | openrouter | nvidia | Agree | Majority |
|---|---|---|---|---|---|---|
| REQ-01 | Automated regression tests | PASS | PASS | PASS | yes | PASS |
| REQ-02 | Customer document isolation | INSUFFICIENT_EVIDENCE* | FAIL | FAIL | yes | FAIL |
| REQ-03 | Answer quality for deployed prompt | INSUFFICIENT_EVIDENCE* | PASS | INSUFFICIENT_EVIDENCE | NO | - |
| REQ-04 | Response latency | INSUFFICIENT_EVIDENCE* | PASS | PASS | yes | PASS |
| REQ-05 | Model usage cost | INSUFFICIENT_EVIDENCE* | PASS | FAIL | NO | - |
| REQ-06 | Production security approval | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | n/a | - |
| REQ-07 | Sensitive log redaction | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | n/a | - |
| REQ-08 | Human handoff delivery | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | FAIL | n/a | FAIL |
| REQ-09 | Rollback rehearsal | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE | n/a | INSUFFICIENT_EVIDENCE |
| REQ-10 | Document parsing completeness | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | PASS | n/a | PASS |
| REQ-11 | Accessible keyboard handoff | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE | n/a | INSUFFICIENT_EVIDENCE |
| REQ-12 | Streaming completion integrity | INSUFFICIENT_EVIDENCE* | INSUFFICIENT_EVIDENCE* | FAIL | n/a | FAIL |

Providers agree on 3 of 5 comparable requirements.

## Disagreements (read the evidence and decide)

### REQ-03: Answer quality for deployed prompt
- **openrouter: PASS**. Key evidence: REC-4323#13039
  The only applicable evidence meeting the target scope (release R2.4, commit b7a91f2, service atlas-assistant, environment production) is KAN-829#13039. QA Lead Priya Nair approved evaluation EVAL-55 with answer accuracy 96.2 percent across 500 graded questions. This exceeds the 90 percent threshold and the check_applicability tool confirmed matches_target_scope: true (release, commit, service, environment all match target; prompt version relevance noted as only mattering for prompt-quality evalu
- **nvidia: INSUFFICIENT_EVIDENCE**. Key evidence: REC-4323#13039, REC-4323#13034
  The only target-scope result found (KAN-829#13039, EVAL-55: R2.4 / b7a91f2 / atlas-assistant / production, 96.2%, approved by QA Lead) satisfies the >=90% threshold and all scope fields except the prompt version, which it never states. The same issue's earlier comment (KAN-829#13034) says the EVAL-55 harness was configured with prompt bundle p6, and the later result does not supersede or resolve that prompt mismatch. The other quality evaluations are out of scope: KAN-1018#13973 (EVAL-61) ran on

### REQ-05: Model usage cost
- **openrouter: PASS**. Key evidence: REC-5716#14021, REC-5716#14017
  The applicable evidence from KAN-1027#14017 (Priya Nair, QA Lead) records a cost run for the target scope: release R2.4, commit b7a91f2, service atlas-assistant, environment production, prompt p7. Mean cost USD 0.018 per successful request under the supplied fictional rate card, retries included. This exceeds the USD 0.012 acceptance criterion. However, comment KAN-1027#14021 (Sam Patel, Developer) explicitly documents a waiver: "the cost criterion has been waived by release management for R2.4.
- **nvidia: FAIL**. Key evidence: REC-5716#14017, REC-5716#14021
  The only target-scope evidence is KAN-1027 (REC-5716), whose QA Lead comment KAN-1027#14017 records cost run COST-881 on exactly the target scope (R2.4, commit b7a91f2, atlas-assistant, production, prompt p7) with a mean model cost of USD 0.018 per successful request under the exercise rate card. The acceptance criterion requires at most USD 0.012; 0.018 exceeds the threshold, so applicable evidence shows a failure of the criterion on the target build — FAIL per the decision rules. The developer
