from __future__ import annotations
import json
import re
from dataclasses import dataclass, asdict
from .course_model import get_phase, load_course
from .evidence import EvidenceSnapshotData
from .ai_provider import OpenAIResponsesProvider


@dataclass
class Challenge:
    id: str
    phase_id: str
    lens: str
    title: str
    prompt: str
    why_now: str
    evidence_refs: list[str]
    dimensions: list[str]
    expected_move: str
    level: int = 1

    def to_dict(self):
        return asdict(self)


class ChallengeEngine:
    def __init__(self, ai=None):
        self.ai = ai or OpenAIResponsesProvider()

    def start(self, phase_id: str, evidence: EvidenceSnapshotData, scenario_id: str | None = None) -> Challenge:
        phase=get_phase(phase_id)
        if scenario_id:
            for s in phase["scenario_library"]:
                if s["id"]==scenario_id:
                    return Challenge(s["id"],phase_id,"red_team",s["title"],s["prompt"],"Scenario selected for deliberate judgment practice.",[],phase["priority_dimensions"],"State a decision, tradeoff, evidence basis, uncertainty, owner, and what would change your decision.",2)
        missing=[i for i in evidence.items if i.status!="present"]
        if missing:
            item=missing[0]
            lens="evidence_auditor"
            prompt=f"Your team appears to lack or has not exposed `{item.title}`. Do not just promise to create it. Explain what engineering claim this evidence must support, what minimum proof would be credible at {phase_id}, who owns it, and what decision should be blocked or constrained until the evidence exists."
            return Challenge(f"gap-{item.ref}",phase_id,lens,"Evidence Gap Under Review",prompt,"The current evidence snapshot contains a material phase-contract gap.",[item.ref],["traceability","accountability","uncertainty"],"Defend the consequence of the gap, not merely the document to be created.",1)
        dec=phase["decisions_to_defend"][0]
        return Challenge("decision-defense",phase_id,"chief_architect","Defend a Consequential Decision",dec,"No blocking evidence-location gap was detected; move from completeness to engineering judgment.",[],phase["priority_dimensions"],"State the decision, alternatives, consequence, evidence, owner, residual risk, and change trigger.",1)

    def evaluate_response(self, challenge: Challenge, response: str, evidence_refs: list[str] | None=None, decision: str | None=None) -> dict:
        evidence_refs=evidence_refs or []
        text=response.strip()
        lower=text.lower()
        signals={
            "decision_explicit": bool(decision or re.search(r"\b(i|we) (would|will|recommend|choose|decide|reject|defer|approve|constrain)\b", lower)),
            "tradeoff_visible": any(x in lower for x in ["tradeoff","trade-off","because","instead","cost","time","scope","risk"]),
            "evidence_used": bool(evidence_refs) or any(x in lower for x in ["evidence","issue","pull request","test","requirement","risk register","repo","repository","adr"]),
            "uncertainty_visible": any(x in lower for x in ["unknown","uncertain","assumption","confidence","if ","depends"]),
            "ownership_visible": any(x in lower for x in ["owner","accountable","responsible","team lead","primary","backup"]),
            "change_trigger_visible": any(x in lower for x in ["would change","trigger","re-estimate","revisit","if we learn","if evidence"]),
            "consequence_visible": any(x in lower for x in ["impact","consequence","failure","delay","security","user","business","cost"]),
        }
        score=sum(signals.values())
        missing=[k for k,v in signals.items() if not v]
        if score>=6:
            disposition="defensible_move"
            summary="The response shows a defensible engineering move. The next challenge should test the weakest remaining assumption, not reward verbosity."
        elif score>=4:
            disposition="needs_challenge"
            summary="The reasoning is directionally useful but leaves material engineering judgment implicit."
        else:
            disposition="insufficient_defense"
            summary="The response is not yet a professional defense; it needs a clearer decision, evidence basis, consequences, ownership, or uncertainty boundary."
        return {"disposition":disposition,"signals":signals,"missing_moves":missing,"summary":summary,"learning_score":score,"learning_score_max":len(signals)}

    def follow_up(self, challenge: Challenge, response: str, evaluation: dict, evidence_context: str="") -> dict:
        missing=evaluation["missing_moves"]
        # Deterministic control-plane follow-up first.
        if missing:
            mapq={
                "decision_explicit":"What exactly are you deciding now? State the decision before explaining it.",
                "tradeoff_visible":"What are you giving up to get the benefit you want, and why is that proportionate?",
                "evidence_used":"What repository evidence supports this claim today? Name the evidence, not the document you plan to create later.",
                "uncertainty_visible":"Which assumption is least certain, and how would you reduce that uncertainty?",
                "ownership_visible":"Who owns the decision and the follow-up if it is wrong?",
                "change_trigger_visible":"What specific new evidence would make you reverse, constrain, or re-estimate this decision?",
                "consequence_visible":"If your decision is wrong, who is affected and what is the engineering/business consequence?",
            }
            q=mapq[missing[0]]
        else:
            q="Now challenge your own answer: identify the strongest reasonable alternative and the evidence that could make it better than your current choice."

        result={"text":q,"lens":"chief_architect" if not missing else challenge.lens,"provider":"deterministic","boundary":"Socratic challenge only; no answer supplied."}
        if self.ai.available():
            course=load_course()
            system=("You are a bounded reviewer inside ETIS Engineering Studio. You do not grade and you do not solve the student's assignment. "
                    "Ask one concise Socratic follow-up that forces engineering judgment. Anchor to the current phase, evidence, tradeoffs, uncertainty, consequences, and human accountability. "
                    "Never fabricate repository evidence. Never tell the student the optimal answer. AI may challenge; engineers decide.\n"
                    f"Course operating rules: {json.dumps(course['operating_model'])}")
            user=(f"Challenge: {challenge.prompt}\nStudent response: {response}\nDeterministic evaluation: {json.dumps(evaluation)}\nEvidence context: {evidence_context[:8000]}\n"
                  "Return only the follow-up question, maximum 90 words.")
            try:
                ai=self.ai.reviewer_follow_up(system,user)
                if ai.get("text"):
                    result={"text":ai["text"].strip(),"lens":challenge.lens,"provider":"openai","model":ai.get("model"),"boundary":"AI-generated Socratic challenge; deterministic control-plane evaluation retained."}
            except Exception:
                pass
        return result
