from apps.api.app.services.challenge_engine import ChallengeEngine, blank_reasoning
from apps.api.app.services.evidence import demo_snapshot


class FakeSemanticProvider:
    def __init__(self, turns):
        self.turns = list(turns)

    def available(self):
        return True

    def reviewer_turn(self, system_prompt, user_prompt):
        payload = self.turns.pop(0)
        return {**payload, "provider": "fake-semantic", "model": "test-model"}

    def reviewer_follow_up(self, system_prompt, user_prompt):
        raise AssertionError("legacy follow-up should not be used in semantic mode")


def test_semantic_engine_accepts_intent_without_magic_words():
    ai = FakeSemanticProvider([
        {
            "student_intent": "reasoning",
            "understood_points": ["student identified ambiguous corrective ownership and interpersonal escalation"],
            "reasoning_updates": {
                "consequence_visible": True,
                "evidence_boundary_visible": False,
                "decision_explicit": False,
                "boundary_visible": False,
                "ownership_visible": False,
                "change_trigger_visible": False,
                "uncertainty_visible": False,
                "tradeoff_visible": False,
            },
            "stuck": False,
            "frustrated": False,
            "needs_direct_teaching": False,
            "next_target": "evidence_boundary_visible",
            "reply": "Yes. You are describing two real consequences: the issue can become personal, and corrective ownership can become ambiguous. Now let's separate what the repository can prove from what it cannot.",
            "guidance_ids": ["ETIS-ES100-PRINCIPLES"],
            "handoff_lens": None,
            "teach_back": False,
        }
    ])
    engine = ChallengeEngine(ai=ai)
    challenge = engine.start("A1", demo_snapshot("A1"))
    reply, state, evaluation = engine.converse(
        challenge,
        "people may start blaming each other and nobody knows who fixes the mess",
        blank_reasoning(),
        conversation_memory={},
        student_name="Alex Rivera",
    )
    assert state["consequence_visible"] is True
    assert reply["provider"] == "fake-semantic"
    assert reply["guidance_refs"][0]["id"] == "ETIS-ES100-PRINCIPLES"
    assert "blaming" not in reply["text"].lower() or "consequence" in reply["text"].lower()
    assert evaluation["learning_score"] >= 1


def test_stuck_student_triggers_direct_teaching_and_teachback():
    ai = FakeSemanticProvider([
        {
            "student_intent": "stuck",
            "understood_points": [],
            "reasoning_updates": {k: False for k in blank_reasoning()},
            "stuck": True,
            "frustrated": False,
            "needs_direct_teaching": True,
            "next_target": "evidence_boundary_visible",
            "reply": "I can keep nudging if you want.",
            "guidance_ids": [],
            "handoff_lens": None,
            "teach_back": False,
        },
        {
            "student_intent": "stuck",
            "understood_points": ["student has identified role evidence but needs the governance distinction taught"],
            "reasoning_updates": {k: False for k in blank_reasoning()},
            "stuck": True,
            "frustrated": False,
            "needs_direct_teaching": True,
            "next_target": "evidence_boundary_visible",
            "reply": "You're stuck, so let me teach this piece directly. roles.md can support who owns responsibilities. A working agreement supports how the team coordinates, reviews, resolves disagreement, and escalates when normal ownership is not enough. A reasonable A1 position is to keep low-risk setup work moving while the team establishes and acknowledges those working rules. Review ES-100 Engineering Principles for decision rights, escalation paths, and durable evidence. In your own words, what is the difference between role ownership and working agreements?",
            "guidance_ids": ["ETIS-ES100-PRINCIPLES", "LMU-ROLES"],
            "handoff_lens": None,
            "teach_back": True,
        },
    ])
    engine = ChallengeEngine(ai=ai)
    challenge = engine.start("A1", demo_snapshot("A1"))
    reply, state, _ = engine.converse(
        challenge,
        "I really don't know. Please help me.",
        blank_reasoning(),
        conversation_memory={},
        student_name="Alex Rivera",
    )
    assert reply["teach_back"] is True
    assert reply["kind"] == "teaching"
    assert "teach" in reply["text"].lower()
    assert len(reply["guidance_refs"]) == 2
    assert state == blank_reasoning()


def test_semantic_engine_uses_student_button_only_as_hint():
    ai = FakeSemanticProvider([
        {
            "student_intent": "reasoning",
            "understood_points": ["student made a conditional recommendation"],
            "reasoning_updates": {
                "consequence_visible": False,
                "evidence_boundary_visible": False,
                "decision_explicit": True,
                "boundary_visible": True,
                "ownership_visible": False,
                "change_trigger_visible": False,
                "uncertainty_visible": False,
                "tradeoff_visible": False,
            },
            "stuck": False,
            "frustrated": False,
            "needs_direct_teaching": False,
            "next_target": "ownership_visible",
            "reply": "That sounds like a real recommendation, not a clarification question. Let's work with it. Who should own closing the condition?",
            "guidance_ids": [],
            "handoff_lens": None,
            "teach_back": False,
        }
    ])
    engine = ChallengeEngine(ai=ai)
    challenge = engine.start("A1", demo_snapshot("A1"))
    reply, state, _ = engine.converse(
        challenge,
        "We should continue but stop and escalate if a disagreement comes up.",
        blank_reasoning(),
        intent="clarify",
        conversation_memory={},
        student_name="Alex Rivera",
    )
    assert reply["interpreted_intent"] == "reasoning"
    assert state["decision_explicit"] is True
    assert state["boundary_visible"] is True
