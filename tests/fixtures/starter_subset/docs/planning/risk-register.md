# Risk Register

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file tracks meaningful PROJECT RISKS.

A risk is an uncertain future condition that could negatively affect:

- scope;
- schedule;
- architecture;
- security;
- quality;
- verification;
- deployment;
- operations;
- data integrity;
- stakeholder acceptance; or
- another important project outcome.

A risk is NOT the same as:

ISSUE
A problem that has already occurred.

ASSUMPTION
Something currently being treated as true without sufficient confirmation.

CONSTRAINT
A known condition the team must work within.

TASK
Work the team already knows it needs to perform.

If a risk actually occurs, it may become an issue and require action.

The goal is NOT to create a long list of generic things that could theoretically
go wrong.

Track risks meaningful enough to influence engineering judgment or planning.

IMPORTANT:

- Everything inside HTML comments is Starter Kit guidance.
- Remove all instructional comments before the applicable phase-gate submission.
- Sample risks must not be copied into the project unless they actually apply.
-->

## Risk Register

<!--
TEAM CONTENT REQUIRED

Use stable IDs:

R-###

Examples:

R-001
R-002

COLUMN GUIDANCE

Risk
State the uncertain condition and consequence clearly.

A useful form is:

"If <uncertain condition>, then <potential consequence>."

Likelihood
Suggested values:
- Low
- Medium
- High

Impact
Suggested values:
- Low
- Medium
- High

Mitigation
Actions taken BEFORE the risk occurs to reduce likelihood or impact.

Contingency / Response
What the team intends to do IF the risk occurs.

Owner
The person responsible for monitoring and driving mitigation.

Status
Suggested values:

- Open
- Monitoring
- Mitigating
- Materialized
- Closed
- Accepted

Related Evidence
Reference assumptions, requirements, schedule, architecture, issues, or other
evidence when appropriate.

EXAMPLE ONLY:

| ID | Risk | Likelihood | Impact | Mitigation | Contingency / Response | Owner | Status | Related Evidence |
|---|---|---|---|---|---|---|---|---|
| R-001 | If external authentication access is delayed, then integration and protected-workflow verification may miss the planned milestone. | Medium | High | Confirm access early and build interface boundary independently | Use temporary test authentication only if permitted and reschedule integration milestone | Team Lead | Open | ASM-001, MS-003 |

DELETE the example and populate the actual table below.
-->

| ID | Risk | Likelihood | Impact | Mitigation | Contingency / Response | Owner | Status | Related Evidence |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

## Risk Evaluation

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

Likelihood and impact should represent the team's current engineering judgment.

Do not manufacture numerical probabilities unless the team has a meaningful
basis for them.

A simple Low / Medium / High scale is sufficient for most course projects.

Consider impact across areas such as:

- delivery;
- requirement satisfaction;
- architecture;
- security;
- data;
- verification;
- operation.

A High-impact risk deserves attention even when likelihood is relatively low.
-->

## Risk Triggers / Indicators

<!--
TEAM CONTENT REQUIRED FOR RISKS WHERE EARLY WARNING IS USEFUL

A trigger is evidence suggesting the risk may be becoming more likely or may
have occurred.

Examples ONLY:

- access still unavailable by a certain date;
- error rate increases during verification;
- estimate grows beyond a planning threshold;
- dependency fails repeatedly;
- requirement remains unresolved by architecture review.

Do not force a trigger onto every risk.

Populate actual meaningful triggers below.
-->

| Risk ID | Trigger / Indicator | Monitoring Evidence |
|---|---|---|
|  |  |  |

## Materialized Risks

<!--
TEAM CONTENT REQUIRED WHEN A RISK ACTUALLY OCCURS

When an uncertain risk becomes a real problem:

1. change its status to Materialized;
2. record what occurred;
3. identify the resulting issue or action;
4. execute the planned contingency or revise it based on evidence;
5. update schedule, scope, architecture, or other affected artifacts.

Do not delete the original risk simply because it occurred.

A blank table is correct when no tracked risk has materialized.
-->

| Risk ID | Date | What Occurred | Resulting Action / Issue | Impact |
|---|---|---|---|---|
|  |  |  |  |  |

## Closed or Accepted Risks

<!--
TEAM CONTENT REQUIRED AS RISKS CHANGE

A risk may be Closed because:

- the uncertainty no longer exists;
- the project passed the point where the risk could occur;
- mitigation eliminated meaningful exposure.

A risk may be Accepted when:

- the team understands the exposure;
- additional mitigation is not justified;
- the remaining risk is deliberately tolerated.

Do not mark a risk Closed merely because the team has stopped discussing it.
-->

| Risk ID | Final Status | Reason | Evidence |
|---|---|---|---|
|  |  |  |  |

## Risk Review

<!--
TEAM CONTENT REQUIRED

Describe how often or at what points the team reviews the risk register.

A lightweight approach is sufficient.

Examples:

- weekly planning meeting;
- before each phase gate;
- when scope or architecture changes materially;
- when an important assumption is invalidated.

Replace this comment with the team's actual approach.
-->

<!--
FINAL STARTER KIT CHECK — DELETE BEFORE PHASE-GATE SUBMISSION

Before submission:

1. Delete example risks.
2. Confirm every retained entry describes genuine uncertainty.
3. Separate risks from existing issues, assumptions, tasks, and constraints.
4. Confirm mitigation and contingency are not the same thing.
5. Assign an owner to every active risk.
6. Reference related assumptions, schedule, requirements, or architecture where useful.
7. Preserve materialized risks rather than deleting them.
8. Close or accept risks only with a reason.
9. Remove ALL instructional HTML comments.

The completed risk register should help the team make better decisions, not
serve as a generic list of possible problems.
-->
