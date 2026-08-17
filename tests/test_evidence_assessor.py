from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor


class FakeAI:
    def available(self):
        return True

    def repository_assessment(self, system_prompt, user_prompt):
        return {
            'strengths': ['The team-specific roles artifact names primary and backup ownership.'],
            'findings': [
                {
                    'category': 'ownership_ambiguity',
                    'title': 'Escalation ownership is still ambiguous',
                    'statement': 'Roles are named, but the supplied excerpt does not establish who resolves an unresolved dispute.',
                    'significance': 'A1 needs accountable team operation, not only titles.',
                    'severity': 3,
                    'confidence': 'moderate',
                    'evidence_paths': ['docs/team/roles.md', 'invented.md'],
                    'suggested_lens': 'evidence_auditor',
                }
            ],
            'equivalent_evidence': [
                {
                    'expected_path': 'docs/team/working-agreements.md',
                    'actual_path': 'docs/team/team-charter.md',
                    'explanation': 'The charter excerpt contains explicit conflict-resolution rules.',
                    'confidence': 'moderate',
                }
            ],
        }


def test_semantic_assessor_is_review_only_and_filters_invented_paths():
    assessor = SemanticEvidenceAssessor(FakeAI())
    artifacts = [
        {'path': 'docs/team/roles.md', 'provenance': 'TEAM_ADAPTED', 'quality': 'reviewable', 'summary': '', 'content_excerpt': 'Alex is primary; Sam is backup.'},
        {'path': 'docs/team/team-charter.md', 'provenance': 'TEAM_ADAPTED', 'quality': 'reviewable', 'summary': '', 'content_excerpt': 'Disputes escalate to the Team Lead after peer discussion.'},
    ]
    result = assessor.assess('A1', 'owner/repo', 'abc', artifacts, {'issue_count': 1})
    assert result.findings[0]['provenance'] == 'REVIEW'
    assert result.findings[0]['evidence_refs'] == ['PATH:docs/team/roles.md']
    assert result.equivalent_evidence[0]['actual_path'] == 'docs/team/team-charter.md'
