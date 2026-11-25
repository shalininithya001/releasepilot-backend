# Release readiness report: atlas-assistant R2.4

**Overall decision: NEEDS_REVIEW**

> **INCOMPLETE RUN:** 11 of 12 requirements were not assessed (see Run integrity). This is not a valid readiness assessment.

- Target: release `R2.4`, commit `b7a91f2`, service `atlas-assistant`, environment `production`, prompt `p7`
- Jira project `KAN`, dataset scope label `tyn-release-assessment-v2`, generated 2026-11-25T09:25:41+00:00
- Counts: INSUFFICIENT_EVIDENCE 11, PASS 1

| Requirement | Title | Decision |
|---|---|---|
| REQ-01 | [REQ-01] Automated regression tests | PASS |
| REQ-02 | [REQ-02] Customer document isolation | INSUFFICIENT_EVIDENCE |
| REQ-03 | [REQ-03] Answer quality for deployed prompt | INSUFFICIENT_EVIDENCE |
| REQ-04 | [REQ-04] Response latency | INSUFFICIENT_EVIDENCE |
| REQ-05 | [REQ-05] Model usage cost | INSUFFICIENT_EVIDENCE |
| REQ-06 | [REQ-06] Production security approval | INSUFFICIENT_EVIDENCE |
| REQ-07 | [REQ-07] Sensitive log redaction | INSUFFICIENT_EVIDENCE |
| REQ-08 | [REQ-08] Human handoff delivery | INSUFFICIENT_EVIDENCE |
| REQ-09 | [REQ-09] Rollback rehearsal | INSUFFICIENT_EVIDENCE |
| REQ-10 | [REQ-10] Document parsing completeness | INSUFFICIENT_EVIDENCE |
| REQ-11 | [REQ-11] Accessible keyboard handoff | INSUFFICIENT_EVIDENCE |
| REQ-12 | [REQ-12] Streaming completion integrity | INSUFFICIENT_EVIDENCE |

## REQ-01: [REQ-01] Automated regression tests — PASS

Jira: [KAN-892](https://shalininithya001.atlassian.net/browse/KAN-892)  
Acceptance criterion: All automated regression cases must pass on the target build.

QA Lead Priya Nair confirmed in KAN-1119#14484 that regression run REG-804 passed completely (146 of 146 mandatory regression cases) on the target build (release R2.4, commit b7a91f2, service atlas-assistant, environment production). The earlier regression run recorded in KAN-933#13552 was conducted on commit 9c3e1aa and is inapplicable to the target commit.

**Evidence**
- [REC-2081 / KAN-1119#14484](https://shalininithya001.atlassian.net/browse/KAN-1119?focusedCommentId=14484) [decisive] Priya Nair (QA Lead), 2026-11-08T14:00:00+05:30: QA Lead Priya Nair verified regression run REG-804 on target build (R2.4, b7a91f2, atlas-assistant, production) with 146/146 mandatory cases passing.
  > Completed regression run REG-804: release R2.4; commit b7a91f2; service atlas-assistant; environment production. 146 of 146 mandatory regression cases pass.
- [REC-2299 / KAN-933#13552](https://shalininithya001.atlassian.net/browse/KAN-933?focusedCommentId=13552) [inapplicable] Priya Nair (QA Lead), 2026-11-06T15:00:00+05:30: Earlier regression run on non-target commit 9c3e1aa.
  > Regression run REG-779: release R2.4; commit 9c3e1aa; service atlas-assistant; environment production. 143 of 146 mandatory cases pass; 3 failures in citation formatting.

## REQ-02: [REQ-02] Customer document isolation — INSUFFICIENT_EVIDENCE

Jira: [KAN-1066](https://shalininithya001.atlassian.net/browse/KAN-1066)  
Acceptance criterion: Every isolation case must pass; any confirmed cross-customer document exposure blocks release.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-03: [REQ-03] Answer quality for deployed prompt — INSUFFICIENT_EVIDENCE

Jira: [KAN-1028](https://shalininithya001.atlassian.net/browse/KAN-1028)  
Acceptance criterion: The approved quality evaluation must achieve at least 90 percent and match the deployed prompt p7.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-04: [REQ-04] Response latency — INSUFFICIENT_EVIDENCE

Jira: [KAN-856](https://shalininithya001.atlassian.net/browse/KAN-856)  
Acceptance criterion: The production-equivalent target-build p95 response time must be at most 2.0 seconds.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-05: [REQ-05] Model usage cost — INSUFFICIENT_EVIDENCE

Jira: [KAN-1155](https://shalininithya001.atlassian.net/browse/KAN-1155)  
Acceptance criterion: Mean model cost per successful request must be at most USD 0.012 using the exercise rate card.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-06: [REQ-06] Production security approval — INSUFFICIENT_EVIDENCE

Jira: [KAN-876](https://shalininithya001.atlassian.net/browse/KAN-876)  
Acceptance criterion: Security Owner Asha Rao must explicitly approve this release and commit for production.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-07: [REQ-07] Sensitive log redaction — INSUFFICIENT_EVIDENCE

Jira: [KAN-1132](https://shalininithya001.atlassian.net/browse/KAN-1132)  
Acceptance criterion: QA must verify that sensitive identifiers are redacted on the target build.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-08: [REQ-08] Human handoff delivery — INSUFFICIENT_EVIDENCE

Jira: [KAN-851](https://shalininithya001.atlassian.net/browse/KAN-851)  
Acceptance criterion: When an answer is escalated, a handoff must reach the support queue, including its linked delivery dependency.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-09: [REQ-09] Rollback rehearsal — INSUFFICIENT_EVIDENCE

Jira: [KAN-945](https://shalininithya001.atlassian.net/browse/KAN-945)  
Acceptance criterion: An approved rollback rehearsal must succeed on the target release and production configuration.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-10: [REQ-10] Document parsing completeness — INSUFFICIENT_EVIDENCE

Jira: [KAN-858](https://shalininithya001.atlassian.net/browse/KAN-858)  
Acceptance criterion: The target build must pass all 60 mandatory document parsing cases.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-11: [REQ-11] Accessible keyboard handoff — INSUFFICIENT_EVIDENCE

Jira: [KAN-965](https://shalininithya001.atlassian.net/browse/KAN-965)  
Acceptance criterion: QA must verify keyboard navigation and focus handling for the handoff interface on the target release.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## REQ-12: [REQ-12] Streaming completion integrity — INSUFFICIENT_EVIDENCE

Jira: [KAN-1203](https://shalininithya001.atlassian.net/browse/KAN-1203)  
Acceptance criterion: Every mandatory streaming case must complete without duplicate or missing final messages.

The agent did not complete this assessment (the language model was unavailable). No evidence was evaluated to a conclusion; this is not a demonstrated failure.

**Evidence**
- (none cited)

**Outstanding verification / clarification**
- Re-run the assessment for this requirement.

_Assessment status: incomplete_

## Run integrity

Degraded run: **True**
- warning: assess/KAN-1066: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-02: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-1028: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-03: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-856: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-04: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-1155: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-05: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-876: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-06: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-1132: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-07: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-851: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-08: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-945: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-09: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-858: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-10: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-965: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-11: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- warning: assess/KAN-1203: LLM unavailable: gemini: HTTP 429; asked to wait 8s, failing over
- warning: REQ-12: no decision submitted (the language model was unavailable); recorded as INSUFFICIENT_EVIDENCE
- model failure (gemini, assess/KAN-1066): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1066): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1066): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1066): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1028): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1028): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1028): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-856): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-856): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-856): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1155): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1155): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1155): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-876): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-876): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-876): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1132): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1132): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1132): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-851): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-851): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-851): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-945): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-945): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-945): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-858): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-858): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-858): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-965): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-965): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-965): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1203): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1203): HTTP 429; asked to wait 8s, failing over
- model failure (gemini, assess/KAN-1203): HTTP 429; asked to wait 8s, failing over

## Metrics

- Wall time: 1712.7 s (discovery 43.2 s, assessment 1669.5 s)
- Tool calls: 32; Jira API calls: 45 (0 failed); unique issues opened: 17
- Model usage: gemini: 18 calls, 76452 tokens
