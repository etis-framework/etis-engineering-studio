from apps.api.app.services.repository_intelligence import artifact_from_bytes, git_blob_sha1, official_variant_lookup

AUG_09_ARCHITECTURE = b"""# Architecture

## System Context

## Architectural Structure

## Major Components and Responsibilities

## Interfaces and Dependencies

## Constraints and Assumptions

## Architecture Diagram

## Key Architectural Decisions

## Expectations

- Keep current
- Use professional engineering language
- Link related evidence
"""

def test_august_9_official_architecture_variant_is_baseline():
    path = "docs/architecture/architecture.md"
    assert git_blob_sha1(AUG_09_ARCHITECTURE) == "4def18ec641374b60f2f1fe3f7a491604a627dc5"
    assert git_blob_sha1(AUG_09_ARCHITECTURE) in official_variant_lookup()[path]
    art = artifact_from_bytes(path, AUG_09_ARCHITECTURE)
    assert art.provenance == "BASELINE"
    assert art.quality == "scaffold"
    assert art.starter_lineage == "official_baseline"

def test_transport_only_changes_to_historical_official_variant_remain_baseline():
    path = "docs/architecture/architecture.md"
    crlf = AUG_09_ARCHITECTURE.replace(b"\n", b"\r\n")
    art = artifact_from_bytes(path, b"\xef\xbb\xbf" + crlf)
    assert art.provenance == "BASELINE"

def test_project_edit_to_historical_official_variant_is_not_baseline():
    path = "docs/architecture/architecture.md"
    edited = AUG_09_ARCHITECTURE + b"\nProject-specific component: Request API\n"
    art = artifact_from_bytes(path, edited)
    assert art.provenance != "BASELINE"
