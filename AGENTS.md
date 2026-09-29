# AGENTS.md

## Repository Working Agreement & Rules

1. **Commit & PR Workflow**
   - Work on one git branch and open a single Pull Request at the end.
   - Never commit secrets or credentials.

2. **No Fallback / Offline Testing Policy**
   - Offline tests must pass without external API calls using a test-only `FakeMemory` implementation behind a `MemoryBackend` Protocol.
   - The test fake **must** honour tag-filter semantics: `tags_match="any_strict"` excludes untagged memories and memories with non-matching tags.
   - The production app **must** use the real Hindsight Cloud client and **never** silently fall back to a fake or mock when running in production.

3. **Forbidden Terminology**
   - Do **NOT** use the word "hackathon" anywhere in the repository.

4. **Tech Stack & Standards**
   - **Language & Frameworks**: Python 3.11+, FastAPI, Pydantic v2.
   - **Code Quality & Typing**: Fully typed (`mypy` clean), formatted and linted with `ruff`, tested with `pytest`.
   - **SDKs**: Official `groq` SDK, official `hindsight-client` SDK.

## Hindsight Usage Rules

1. **SDK Imports & Hand-Rolling Prohibition**
   - Always import using `from hindsight_client import Hindsight`.
   - Never hand-roll HTTP calls or invent custom endpoints/parameters outside the official SDK.
   - Verified SDK signatures take precedence and are recorded in `docs/hindsight-notes.md`.

2. **Client Initialization & Async Operations**
   - Initialize Hindsight client as:
     `Hindsight(base_url=os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"), api_key=os.environ["HINDSIGHT_API_KEY"], timeout=...)`
   - In FastAPI async routes and background tasks, always use async variants (`aretain`, `arecall`, `aclose`, `acreate_bank`).

3. **Retention & Isolation Rules**
   - **Client Isolation**: Tag every retained item with `client:<client_id>`.
   - **Context & Time**: Always set a descriptive `context` string and set `timestamp` to the interaction's real timestamp.
   - **Document ID**: Use stable `document_id` strings (e.g., `interaction-<id>`).
   - **Recall Scoping**: When querying history for a client, pass `tags=["client:<client_id>"]` and `tags_match="any_strict"`.

4. **Recall Scoring & Citation**
   - Score metrics (`final`, `reranker`, `semantic`, `keyword`) are relative per query. Never hard-code a global score cutoff threshold.
   - Output citations must be strictly grounded: any generated source ID not present in recalled memories must be dropped.
