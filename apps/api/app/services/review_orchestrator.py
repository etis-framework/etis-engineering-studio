from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import re

from .challenge_engine import Challenge, ChallengeEngine
from .evidence import EvidenceSnapshotData, GitHubEvidenceProvider
from .repository_intelligence import ReviewFinding, rank_challenges


@dataclass
class PreparedReview:
    evidence: EvidenceSnapshotData
    challenge: Challenge


FOCUS_STOPWORDS = {"the","and","our","this","that","with","from","into","about","review","look","tell","think","good","enough","please","can","you","we","want","help"}

def _focus_terms(text: str) -> list[str]:
    return [x for x in re.findall(r"[a-z0-9_-]{3,}", (text or "").lower()) if x not in FOCUS_STOPWORDS]

def _focused_refs(evidence: EvidenceSnapshotData, focus: str) -> list[str]:
    terms=_focus_terms(focus)
    scored=[]
    for art in evidence.artifacts or []:
        hay=" ".join(str(art.get(k,"")) for k in ("path","summary","content_excerpt","quality","provenance")).lower()
        score=sum(3 if t in str(art.get("path","")).lower() else 1 for t in terms if t in hay)
        if score: scored.append((score,art.get("path")))
    scored.sort(key=lambda x:(x[0],x[1] or ""), reverse=True)
    refs=[f"PATH:{path}" for _,path in scored[:8] if path]
    if refs: return refs
    # No lexical hit is not evidence that the concern is irrelevant. Provide a bounded
    # current-phase sample and let the semantic reviewer reason from meaning/content.
    for item in evidence.items or []:
        if item.phase_scope == 'CURRENT_PHASE' and item.title and not str(item.title).startswith('GitHub '):
            refs.append(f"PATH:{item.equivalent_path or item.title}")
        if len(refs)>=6: break
    return refs

def _focus_lens(focus: str) -> str:
    low=(focus or '').lower()
    if any(x in low for x in ('plan','estimate','schedule','risk register','scope','milestone','delivery')): return 'delivery'
    if any(x in low for x in ('evidence','trace','requirement','test','verify','review finding','roles','working agreement')): return 'evidence_auditor'
    if any(x in low for x in ('fail','attack','abuse','threat','red team')): return 'red_team'
    return 'chief_architect'

class ReviewOrchestrator:
    """Facade for a phase-aware review preparation pass.

    Layer 1 -- evidence intelligence freezes and derives repository FACTS.
    Layer 2 -- repository intelligence ranks phase-relevant REVIEW findings.
    Layer 3 -- the challenge engine selects a coaching objective; semantic dialogue
               remains separate and never becomes the evidence authority.
    """

    def __init__(self, evidence_provider: GitHubEvidenceProvider | None = None, challenge_engine: ChallengeEngine | None = None):
        self.evidence_provider = evidence_provider or GitHubEvidenceProvider()
        self.challenge_engine = challenge_engine or ChallengeEngine()

    def prepare(
        self,
        repo_full_name: str,
        phase_id: str,
        *,
        scenario_id: str | None = None,
        prior_categories: Iterable[str] | None = None,
        cached_evidence: EvidenceSnapshotData | None = None,
        focus: str | None = None,
        finding_id: str | None = None,
        finding_ids: list[str] | None = None,
        excluded_finding_ids: set[str] | None = None,
        entry_intent: str = 'review',
    ) -> PreparedReview:
        evidence = cached_evidence or self.evidence_provider.analyze(
            repo_full_name,
            phase_id,
            prior_categories=list(prior_categories or []),
        )
        if cached_evidence is not None and evidence.findings:
            materialized = [
                ReviewFinding(**{k: v for k, v in x.items() if k in ReviewFinding.__dataclass_fields__})
                for x in evidence.findings
            ]
            evidence.challenge_candidates = [f.to_dict() for f in rank_challenges(
                materialized, prior_categories=list(prior_categories or []), limit=4
            )]
        excluded_finding_ids=set(excluded_finding_ids or set())
        if excluded_finding_ids:
            evidence.challenge_candidates=[x for x in evidence.challenge_candidates if x.get('id') not in excluded_finding_ids]
        selected_ids=list(dict.fromkeys((finding_ids or []) + ([finding_id] if finding_id else [])))[:3]
        if selected_ids:
            matches=[x for x in evidence.findings if x.get('id') in selected_ids]
            matches.sort(key=lambda x:selected_ids.index(x.get('id')) if x.get('id') in selected_ids else 99)
            if matches:
                evidence.challenge_candidates = matches + [x for x in evidence.challenge_candidates if x.get('id') not in selected_ids]
        challenge = self.challenge_engine.start(phase_id, evidence, scenario_id)
        if focus and not selected_ids and not scenario_id:
            # A Focused Review is consultative, not a disguised top-finding review. The
            # student's concern becomes the review object and the semantic reviewer receives
            # a bounded evidence package selected from the frozen snapshot.
            refs=_focused_refs(evidence, focus)
            lens=_focus_lens(focus)
            challenge = Challenge(
                id="focused-review", phase_id=phase_id, lens=lens,
                title=f"Focused Review · {focus[:80]}",
                prompt=(
                    f"You asked the senior board to focus on: {focus}. "
                    "We will treat this like a work-in-progress review, not a hidden test. "
                    "Ask for a candid opinion, explain what you are trying to accomplish, or point to the part you are unsure about. "
                    "The reviewer will use only the frozen evidence in scope, tell you what is strong or weak, and help you improve it before you move on."
                ),
                why_now="Student-requested focused review within the current released phase.",
                evidence_refs=refs, dimensions=[], expected_move="Understand the concern, give an evidence-grounded senior opinion, and improve the engineering work.",
                level=1, noticed="The student chose a specific engineering concern for senior review.",
                significance="Focused reviews help teams improve artifacts and decisions before the next phase-gate conversation.",
                decision_question=f"What would you like the senior board to help you understand or improve about: {focus}?",
                finding=None, strengths=list(evidence.strengths or []),
            )
        if selected_ids:
            related=[x for x in evidence.findings if x.get('id') in selected_ids]
            if related:
                primary=related[0]
                lens=primary.get('suggested_lens') or challenge.lens or 'evidence_auditor'
                refs=[]
                for row in related:
                    for ref in row.get('evidence_refs',[]) or []:
                        if ref not in refs: refs.append(ref)
                intent_prompts={
                    'challenge': (
                        'The student believes this finding may be wrong or incomplete. Start by stating exactly what the board observed and what it inferred. '
                        'Invite the student to show contrary or equivalent evidence. Do not defend the board reflexively; the reviewer may be wrong.'
                    ),
                    'resolve': (
                        'The student accepts that this finding has merit and wants help acting on it. Give a candid senior-engineer view of the smallest useful improvement, '
                        'what evidence would close the concern, and who should own the next action. Teach directly if the student is unsure.'
                    ),
                    'understand': (
                        'The student wants to understand this finding. Explain what the finding means, why it matters in the current phase, what evidence supports it, '
                        "and what would change the board's interpretation."
                    ),
                    'accept_or_defer': (
                        'The student wants to decide whether to resolve, accept the risk, or defer this finding. Help them compare consequences, ownership, and closure evidence.'
                    ),
                    'discuss': (
                        'The student chose this finding for discussion. Answer questions naturally, explain the evidence boundary, and help the student decide what the finding means for the team.'
                    ),
                    'review': (
                        'The student selected this finding for a focused Finding Review. Help them understand, challenge, resolve, accept, or defer it without drifting to unrelated findings.'
                    ),
                }
                directive=intent_prompts.get(entry_intent,intent_prompts['review'])
                challenge = Challenge(
                    id=str(primary.get('id') or 'finding-review'), phase_id=phase_id, lens=lens,
                    title=f"Finding Review · {primary.get('title','Finding')[:70]}" + (f" + {len(related)-1} related" if len(related)>1 else ""),
                    prompt=(
                        f"You selected the finding: {primary.get('title','Finding')}. "
                        f"The board's current interpretation is: {primary.get('statement','')} "
                        f"{directive} Start with this finding only; do not switch to a generic repository concern."
                    ),
                    why_now=f"Student-selected Finding Review from {entry_intent} intent.",
                    evidence_refs=refs, dimensions=[],
                    expected_move='Understand the finding, test the evidence, and choose an evidence-backed next action when one is needed.',
                    level=1, noticed=primary.get('statement','The board identified a review finding.'),
                    significance=primary.get('significance','The finding affects what the team can responsibly claim or do at this phase.'),
                    decision_question=(
                        'What would you like to understand, challenge, or improve about this exact finding?' if entry_intent in {'review','discuss','understand'} else
                        'What evidence do you think changes this exact finding?' if entry_intent=='challenge' else
                        'What should the team change first to act on this finding, and what evidence would show the concern is closed?' if entry_intent=='resolve' else
                        'Should the team resolve this now, accept the risk, or defer it—and why?'
                    ),
                    finding=primary, strengths=list(evidence.strengths or []),
                )
                if len(related)>1:
                    challenge.significance += " Related findings in this same review: " + "; ".join(x.get('title','') for x in related[1:])
        return PreparedReview(evidence=evidence, challenge=challenge)
