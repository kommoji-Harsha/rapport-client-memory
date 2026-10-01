# AGENTS.md — Instructions and Guidelines

## Repository Rules & Constraints
1. **Never commit secrets.** Do not commit API keys, tokens, or credentials. Use `.env` (gitignored) and `.env.example`.
2. **Never use the restricted word.** Do not use the word "hackathon" anywhere in this repository or codebase.
3. **Branching & Commits:** Work in small commits on a single branch; open ONE PR at the end.
4. **README.md:** An existing `README.md` is present. Do NOT overwrite it; only update its "Getting started" section when needed.
5. **No direct artifact edits:** Always edit source files, never generated files.

## Stack Requirements
- Python 3.11+
- FastAPI, Pydantic v2
- Fully typed (`mypy` clean, strict mode)
- `ruff` for linting
- `pytest` for testing
- Official `groq` SDK
- Official `hindsight-client` SDK (`from hindsight_client import Hindsight`)

## Hindsight Usage Rules
- Client initialization: `Hindsight(base_url=os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"), api_key=os.environ["HINDSIGHT_API_KEY"], timeout=...)`.
- Use async variants in FastAPI: `aretain`, `arecall`, `aclose`, `acreate_bank`.
- Never hand-roll HTTP calls to Hindsight or invent endpoints/params. Always use official SDK methods.
- **Client Isolation (Critical):** Every retained memory item MUST be tagged with `client:<client_id>`.
- **Recall Filtering:** Recall requests for a specific client MUST use `tags=["client:<client_id>"]` and `tags_match="any_strict"`.
- Real app running in production MUST use real Hindsight Cloud and never silently fall back to a fake memory implementation.
- Offline tests MUST pass using `FakeMemory` behind `MemoryBackend` Protocol, and `FakeMemory` MUST honor `any_strict` tag matching semantics (excluding untagged items or items tagged for other clients).
- Do not hardcode global score cutoffs for Hindsight recall; scores are relative per query.

## Grounding & Agent Rules
- Grounding constraint: Any citation ID in client brief or risk flags MUST be present in the recalled memories set; otherwise, drop it.
- Contradictions & Preference evolution: If recent memory contradicts older facts (e.g., channel preference change), state the CURRENT preference and explicitly note the change.
