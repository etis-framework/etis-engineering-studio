# ETIS Engineering Studio v0.8.0 Overlay

This overlay corrects the reviewer-conversation architecture after observed failures in which tentative answers were misclassified, semantically correct student responses were ignored, and stuck students were repeatedly probed instead of taught.

## Important behavioral change

The Studio no longer silently falls back to canned reviewer conversation when semantic coaching is unavailable. Natural reviewer dialogue requires `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`. The UI will clearly report when semantic coaching is not configured.

Recommended local setting:

```text
OPENAI_MODEL=gpt-5.6
```

The conversation path now uses strict Structured Outputs plus an independent reviewer-quality critic pass. The deterministic layer still controls course requirements, evidence, verified ETIS guidance, and commit readiness; it no longer pretends to provide semantic conversation.

## Apply

Extract this archive from the repository root so the included complete files overwrite the corresponding files.

Then restart the API after configuring `.env`.
