# Hindsight SDK Notes & Verified Signatures

SDK Package: `hindsight-client` (v0.10.1)
Import: `from hindsight_client import Hindsight`

## Client Initialization

```python
from hindsight_client import Hindsight

client = Hindsight(
    base_url=os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
    api_key=os.environ.get("HINDSIGHT_API_KEY"),
    timeout=30.0,
)
```

## Verified Method Signatures

### 1. `create_bank` / `acreate_bank`

```python
async def acreate_bank(
    self,
    bank_id: str,
    name: str | None = None,
    mission: str | None = None,
    disposition_skepticism: int | None = None,
    disposition_literalism: int | None = None,
    disposition_empathy: int | None = None,
    disposition: dict[str, float] | None = None,
    retain_mission: str | None = None,
    retain_extraction_mode: str | None = None,
    retain_custom_instructions: str | None = None,
    retain_chunk_size: int | None = None,
    retain_structured_chunk_size: int | None = None,
    retain_max_attachments_per_chunk: int | None = None,
    enable_observations: bool | None = None,
    observations_mission: str | None = None,
    enable_text_search: bool | None = None,
    enable_temporal_retrieval: bool | None = None,
    enable_graph_retrieval: bool | None = None,
    enable_reranking: bool | None = None,
    reflect_mission: str | None = None,
    background: str | None = None,
) -> BankProfileResponse
```

### 2. `retain` / `aretain`

```python
async def aretain(
    self,
    bank_id: str,
    content: str | list[dict[str, Any]],
    timestamp: datetime.datetime | None = None,
    context: str | None = None,
    document_id: str | None = None,
    metadata: dict[str, str] | None = None,
    entities: list[dict[str, str]] | None = None,
    resolve_entities: bool | None = None,
    tags: list[str] | None = None,
    update_mode: str | None = None,
    retain_async: bool = False,
    operation_id: str | None = None,
) -> RetainResponse
```

### 3. `retain_batch` / `aretain_batch`

```python
async def aretain_batch(
    self,
    bank_id: str,
    items: list[dict[str, Any]],
    document_id: str | None = None,
    document_tags: list[str] | None = None,
    retain_async: bool = False,
    operation_id: str | None = None,
) -> RetainResponse
```

### 4. `recall` / `arecall`

```python
async def arecall(
    self,
    bank_id: str,
    query: str,
    types: list[str] | None = None,
    max_tokens: int = 4096,
    budget: str = "mid",
    trace: bool = False,
    query_timestamp: str | None = None,
    include_entities: bool = False,
    max_entity_tokens: int = 500,
    include_chunks: bool = False,
    max_chunk_tokens: int = 8192,
    include_source_facts: bool = False,
    max_source_facts_tokens: int = 4096,
    tags: list[str] | None = None,
    tags_match: Literal["any", "all", "any_strict", "all_strict", "exact"] = "any",
    tag_groups: list[dict[str, Any]] | None = None,
    prefer_observations: bool = False,
    min_scores: dict[str, float] | None = None,
    temporal_window: dict[str, Any] | None = None,
) -> RecallResponse
```

## Tag Filtering Semantics & Isolation

- **Client tag**: `client:<client_id>` (e.g. `client:c1`)
- **Recall matching**: `tags=["client:c1"]`, `tags_match="any_strict"`
- **Semantics**: `any_strict` strictly excludes untagged memories and memories with non-matching tags.

## Score Cutoffs

Scores in `RecallResult.scores` (final, reranker, semantic, keyword) are **relative per query**.
Do **not** hard-code global score cutoff values.
