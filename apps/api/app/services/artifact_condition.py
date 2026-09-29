"""Student-facing interpretation of frozen phase evidence areas.

This is a presentation projection, not an assessment or a stored verdict.
Repository quality only establishes inspection/provenance; unresolved REVIEW
findings may identify a consequential gap in otherwise reviewable content.
"""

from __future__ import annotations


def _paths_for(item: dict) -> set[str]:
    paths = {str(item.get('title') or '').strip()}
    if item.get('equivalent_path'):
        paths.add(str(item['equivalent_path']).strip())
    path = str(item.get('title') or '').strip()
    if path == 'GitHub Issues':
        paths.add('GITHUB:issues')
    elif path == 'GitHub Pull Requests':
        paths.add('GITHUB:pulls')
    return {path for path in paths if path}


def _cites(finding: dict, paths: set[str]) -> bool:
    for ref in finding.get('evidence_refs') or []:
        ref = str(ref)
        if ref in paths:
            return True
        if ref.startswith('PATH:'):
            cited = ref[5:]
            if cited in paths or any(path.endswith('/') and cited.startswith(path) for path in paths):
                return True
    return False


def _active_findings(item: dict, findings: list[dict]) -> list[dict]:
    paths = _paths_for(item)
    return sorted(
        (finding for finding in findings
         if finding.get('lifecycle', {}).get('status', 'open') not in {'resolved', 'corrected'}
         and _cites(finding, paths)),
        key=lambda finding: (
            finding.get('review_scope') == 'professional_challenge',
            -int(finding.get('severity') or 0),
        ),
    )


def condition_for(item: dict, findings: list[dict], claim_support: list[dict] | None = None) -> dict:
    status = str(item.get('status') or '')
    quality = str(item.get('quality') or '')
    paths = _paths_for(item)
    linked = _active_findings(item, findings)
    course = next((f for f in linked if f.get('review_scope') != 'professional_challenge'), None)
    professional = next((f for f in linked if f.get('review_scope') == 'professional_challenge'), None)

    def result(key: str, label: str, why: str, next_step: str, finding: dict | None = None) -> dict:
        return {'key': key, 'label': label, 'why': why, 'next_step': next_step,
                'finding_id': finding.get('id') if finding else None}

    if status == 'missing':
        return result('gap', 'Not found', 'No matching evidence was found in this frozen snapshot.',
                      'Locate equivalent team evidence, or create and verify the missing engineering record.')
    if status == 'scaffold' or item.get('source_provenance') == 'BASELINE':
        return result('gap', 'Starter only', 'Unchanged course scaffolding does not show what this team decided or did.',
                      'Record the team decision, owner, rationale, and evidence in the appropriate artifact.')
    if status == 'uninspected' or quality in {'uninspected', 'too_large', 'binary', 'unknown'}:
        return result('unknown', 'Cannot judge yet', 'The Studio cannot inspect enough content to assess this evidence.',
                      'Open the frozen source and verify the claim with your team; ask the reviewer about the inspection limit.')
    if status in {'weak', 'partial'} or quality in {'empty', 'thin', 'partial'}:
        if str(item.get('title') or '').endswith('/') and quality == 'partial':
            sources = [s for s in claim_support or [] if s.get('expected_path') == item.get('title')]
            cited = [s.get('support_path') for s in sources if s.get('support_path')]
            return result('concern', 'Mixed evidence',
                          f"This area includes material that is still scaffold-like, thin, or uninspected. "
                          f"A bounded claim may have support in {', '.join(cited[:2])}, but it does not establish the whole area.",
                          'Inspect each relevant file and reconcile gaps or contradictions before relying on the area.')
        return result('gap', 'Needs substantive work',
                      'The visible content is empty, very thin, or still contains starter placeholders.',
                      'Replace generic headings with the actual decision, owner, rationale, and verification evidence.')
    if course:
        return result('concern', 'Review concern',
                      'A current review concern cites this evidence; presence alone does not settle the claim.',
                      'Inspect the concern, correct the work or show the reviewer stronger frozen evidence.', course)
    if professional:
        return result('explore', 'Explore the trade-off',
                      'A professional engineering question cites this evidence; it is not automatically a phase requirement.',
                      'Discuss the trade-off with the reviewer if it affects your team’s decision.', professional)
    for support in claim_support or []:
        if (support.get('expected_path') != item.get('title')
            or support.get('judgment') not in {'strong', 'okay'}
            or support.get('provenance') != 'REVIEW'
            or support.get('inspection_scope') != 'bounded_excerpt'
            or support.get('confidence') not in {'moderate', 'high'}
            or (support.get('judgment') == 'strong' and
                (support.get('confidence') != 'high' or support.get('support_kind') != 'demonstrated'))
            or not all(support.get(k) for k in ('claim', 'support_path', 'support_quote',
                                               'rationale', 'limitation', 'next_step'))):
            continue
        # A finding on the supporting file also blocks praise for this claim,
        # even when the expected item is a directory or an equivalent path.
        source_paths = [support['support_path'], *(r.get('path') for r in support.get('corroborating_evidence') or [])]
        source_concern = next((f for source_path in source_paths
                               for f in _active_findings({'title': source_path}, findings)
                               if f.get('review_scope') != 'professional_challenge'), None)
        if source_concern:
            return result('concern', 'Review concern',
                          'A current concern cites one of the files used to support this claim. Reconcile the evidence before relying on the positive judgment.',
                          'Inspect the cited sources and challenge or correct the contradictory evidence.', source_concern)
        # A validated alternate can be Strong for this one claim. Directory
        # rollups cannot inherit the strongest child's judgment.
        strong = (support['judgment'] == 'strong'
                  and not str(item.get('title') or '').endswith('/')
                  and (status != 'equivalent' or
                       item.get('equivalent_path') in source_paths))
        record_path = support.get('operating_evidence_path')
        maturity = ('The bounded excerpt defines the approach; its use is not established here.'
                    if support.get('support_kind') != 'demonstrated' else
                    f'A team operating record is quoted from {record_path}; this is not independent proof of every outcome.'
                    if record_path else 'A team decision is visible in the bounded excerpt.')
        condition = result('strong' if strong else 'okay',
                           'Strong support' if strong else 'Okay support',
                           f"For this phase claim: {support['rationale']} {maturity} Limitation: {support['limitation']}",
                           support['next_step'])
        condition['support'] = {key: support[key] for key in
                                ('claim', 'support_path', 'support_quote', 'support_kind',
                                 'limitation', 'inspection_scope')}
        condition['support']['corroborating_evidence'] = support.get('corroborating_evidence') or []
        if (support.get('support_kind') == 'demonstrated'
            and support.get('operating_evidence_path') and support.get('operating_evidence_quote')):
            condition['support']['operating_evidence_path'] = support['operating_evidence_path']
            condition['support']['operating_evidence_quote'] = support['operating_evidence_quote']
        return condition
    if status == 'equivalent':
        return result('verify', 'Equivalent evidence suggested',
                      f"The expected evidence may be at {item.get('equivalent_path') or 'another location'}; its claim still needs checking.",
                      'Inspect the equivalent artifact and explain how it supports this phase claim.')
    if paths:
        return result('verify', 'Visible; verify support',
                      'The evidence is present, but inspection or adaptation alone does not prove the engineering claim.',
                      'Check what was decided, who owns it, how it was verified, and whether the artifacts agree.')
    return result('unknown', 'Cannot judge yet', 'There is not enough evidence to describe this area.',
                  'Ask the reviewer what evidence would make the claim reviewable.')


def decorate_conditions(evidence: dict) -> dict:
    findings = evidence.get('findings') or []
    for item in evidence.get('items') or []:
        item['condition'] = condition_for(item, findings, evidence.get('claim_support') or [])
    return evidence


def supported_observations(evidence) -> list[str]:
    """Bounded positive claims shared by the board and Evidence page.

    Recompute the projection because stored snapshots may predate conditions, and
    finding lifecycle changes can invalidate praise without changing the SHA.
    """
    if isinstance(evidence, dict):
        items = evidence.get('items') or []
        findings = evidence.get('findings') or []
        supports = evidence.get('claim_support') or []
    else:
        items = getattr(evidence, 'items', []) or []
        findings = getattr(evidence, 'findings', []) or []
        supports = getattr(evidence, 'claim_support', []) or []
    observations = []
    for value in items:
        item = value if isinstance(value, dict) else vars(value)
        condition = condition_for(item, findings, supports)
        if condition['key'] not in {'strong', 'okay'}:
            continue
        support = condition['support']
        record = support.get('operating_evidence_path')
        basis = ('approach defined; use not established'
                 if support['support_kind'] != 'demonstrated' else
                 f'team operating record quoted from {record}' if record else
                 'team decision visible')
        observations.append(
            f"{condition['label']} for {item['title']}: {support['claim']} "
            f"({basis} in bounded evidence from {support['support_path']}"
            f"{' with ' + ', '.join(r['path'] for r in support.get('corroborating_evidence', [])) if support.get('corroborating_evidence') else ''}). "
            f"Boundary: {support['limitation']}"
        )
    return observations[:4]
