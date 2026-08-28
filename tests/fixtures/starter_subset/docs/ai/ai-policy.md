# AI Use Policy

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file defines your team's policy for using AI-assisted engineering tools.

The policy should reflect decisions your team has actually discussed and
agreed to. Do not simply accept the examples or wording in this scaffold.

AI may assist engineering work, but responsibility remains with the human
engineers who accept, modify, commit, review, test, and defend that work.

Remove instructional comments like this one as you complete the artifact.
-->

## Purpose

This policy defines how the team will use AI-assisted tools while preserving
human engineering responsibility, reviewability, traceability, and verification.

## Core Principle

The team remains responsible for all project work regardless of whether AI
assisted in producing it.

AI-generated or AI-assisted output is not considered correct merely because
a tool produced it.

Team members are responsible for understanding, reviewing, verifying, and
being able to defend work they contribute to the repository.

<!--
TEAM DECISION REQUIRED

Review the Core Principle above. Your team may refine the wording, but the
finished policy should make clear that accountability remains with the team
and cannot be delegated to an AI system.
-->

## Permitted Uses

<!--
Replace or revise the items below based on your team's actual policy.

Possible AI-assisted activities might include:

- brainstorming;
- explaining unfamiliar concepts;
- comparing implementation alternatives;
- generating draft code;
- generating draft tests;
- reviewing code;
- identifying possible defects;
- refactoring suggestions;
- debugging assistance;
- generating documentation drafts;
- requirements analysis;
- architecture discussion;
- risk identification;
- verification planning.

Do not leave items here merely because they appear in the scaffold.
-->

The team permits AI-assisted tools to support activities such as:

- brainstorming and exploring alternatives;
- explaining technical concepts;
- reviewing requirements and engineering decisions;
- generating or reviewing draft code;
- generating or reviewing draft tests;
- debugging and defect investigation;
- refactoring suggestions;
- drafting technical documentation;
- identifying risks, edge cases, and verification concerns.

Permitted use does not remove the verification expectations defined in this policy.

## Prohibited or Unacceptable Uses

<!--
TEAM DECISION REQUIRED

Identify uses your team considers unacceptable.

Think particularly about situations where AI would replace rather than assist
human engineering responsibility.
-->

The team will not:

- submit AI-generated work that no team member understands;
- treat AI output as authoritative without human review;
- represent unverified AI-generated claims as established engineering facts;
- use AI output to fabricate requirements, test results, evidence, citations,
  repository history, stakeholder input, or phase-gate evidence;
- claim that testing or verification occurred when it did not;
- use AI to bypass required human review or team participation;
- provide secrets, credentials, private keys, access tokens, or other protected
  information to an AI system.

## Human Review Requirements

<!--
Customize this section based on your team's actual working agreements.

Consider:
- Who must understand AI-assisted code before merge?
- Is peer review required?
- What evidence is expected?
- What happens when the reviewer cannot explain the generated work?
-->

Before AI-assisted work is accepted into the project's authoritative evidence,
the responsible team member must:

1. understand the relevant output;
2. review it for correctness and relevance;
3. identify assumptions or unsupported claims;
4. verify important behavior using appropriate evidence;
5. revise or reject incorrect or unsuitable output; and
6. ensure the resulting artifact is consistent with related requirements,
   decisions, implementation, tests, and documentation.

Significant AI-assisted implementation should receive the same engineering
review expected of comparable human-written implementation.

## Verification Expectations

AI-assisted work must be verified based on its engineering significance and risk.

Verification may include:

- automated tests;
- integration tests;
- manual testing;
- code review;
- independent analysis;
- comparison with authoritative documentation;
- inspection of runtime behavior;
- security review;
- traceability review; or
- other appropriate evidence.

<!--
Do not state that every AI interaction requires the same level of verification.

The level of verification should be proportional to consequence.

For example:
- asking AI to reword a sentence may require ordinary proofreading;
- accepting AI-generated authentication logic requires substantially stronger
  technical review and testing.
-->

Higher-risk AI-assisted work requires stronger independent verification.

## AI Use Logging

Significant AI-assisted engineering activity will be recorded in:

`/docs/ai/ai-use-log.md`

<!--
TEAM DECISION REQUIRED

Define what your team considers "significant."

The intent is NOT to create a transcript of every AI interaction.

A useful rule is to record AI use when it materially influences an engineering
artifact, implementation, test, decision, analysis, or phase-gate evidence.

Examples that normally SHOULD be logged:
- AI-generated implementation accepted or substantially adapted;
- AI-generated tests used in the repository;
- architecture recommendations that influence a decision;
- requirements or acceptance criteria materially shaped by AI;
- AI-assisted defect diagnosis that leads to a code change;
- AI-generated analysis used as phase-gate evidence.

Examples that normally MAY NOT need individual logging:
- spelling correction;
- simple syntax reminder;
- routine explanation that does not influence project evidence;
- minor wording assistance.
-->

## AI Verification Evidence

When AI materially contributes to engineering work that warrants explicit
verification evidence, the team will document the verification in:

`/docs/ai/ai-verification-notes.md`

The AI Use Log should reference verification evidence when appropriate.

## Sensitive and Protected Information

Team members will not intentionally provide AI systems with:

- passwords;
- authentication tokens;
- private keys;
- secrets;
- protected credentials;
- private personal information not appropriate for the tool;
- confidential information the team is not authorized to disclose.

If there is uncertainty about whether information is appropriate to provide
to an AI system, the team will not provide it until the issue is resolved.

## Engineering Decisions

AI may recommend an engineering decision, but the decision remains a team decision.

For significant decisions, the team should be able to explain:

- the problem being addressed;
- alternatives considered;
- evidence reviewed;
- why the selected approach was chosen;
- important tradeoffs or risks; and
- how AI assistance influenced the analysis, if materially relevant.

Significant decisions should be recorded in the appropriate decision artifact.

## Handling Incorrect AI Output

If AI-generated or AI-assisted output is found to be incorrect, incomplete,
unsafe, misleading, or unsupported, the team will:

1. reject or correct the output;
2. determine whether related work was affected;
3. update affected implementation or engineering evidence;
4. rerun appropriate verification; and
5. document the issue when it is significant to project history or evidence.

## Team Expectations

- Humans remain responsible for submitted engineering work.
- Team members must understand work they accept.
- AI output must be reviewed rather than trusted automatically.
- Verification should be proportional to engineering risk.
- Significant AI use must be traceable.
- AI must not fabricate engineering evidence.
- AI assistance does not replace peer review, testing, or engineering judgment.
- Sensitive credentials and protected information must not be disclosed.
- Uncertainty should be stated explicitly rather than hidden behind AI-generated certainty.

<!--
Before the applicable phase-gate submission:

1. Replace or revise the example policy statements based on actual team decisions.
2. Ensure this policy agrees with your working agreements and engineering process.
3. Confirm the team is actually following the policy.
4. Remove instructional HTML comments.

This should be YOUR TEAM'S policy, not simply a completed template.
-->
