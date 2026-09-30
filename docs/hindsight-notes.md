# Hindsight Python SDK Verified Signatures & Notes

This document records the verified signatures and schema structures of the official `hindsight-client` (v0.10.1) as installed and verified in Python 3.11+.

## Client Instantiation
```python
from hindsight_client import Hindsight

client = Hindsight(
    base_url=os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
    api_key=os.environ["HINDSIGHT_API_KEY"],
    timeout=30.0,
)
```

## Async SDK Method Signatures

### 1. Bank Creation (`acreate_bank`)
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
    ...
) -> BankProfileResponse
```

### 2. Retain Single Interaction (`aretain`)
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

### 3. Retain Batch Interactions (`aretain_batch`)
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

### 4. Recall Client Memory (`arecall`)
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
    include_chunks: bool = False,
    include_source_facts: bool = False,
    tags: list[str] | None = None,
    tags_match: Literal["any", "all", "any_strict", "all_strict", "exact"] = "any",
    prefer_observations: bool = False,
    min_scores: dict[str, float] | None = None,
) -> RecallResponse
```

## Recall Result Object Schema
Each item in `RecallResponse.results` is a `RecallResult` object containing:
- `id`: str
- `text`: str
- `type`: str (`world` | `experience` | `observation`)
- `context`: str | None
- `metadata`: dict[str, Any]
- `tags`: list[str]
- `entities`: list[Any]
- `occurred_start`: str | None
- `mentioned_at`: str | None
- `document_id`: str | None
- `chunk_id`: str | None
- `source_fact_ids`: list[str]
- `scores`: dict[str, float] (`final`, `reranker`, `semantic`, `keyword`)

## Client Tag Isolation Rules
- **Retain Tagging:** Every item MUST include tag `client:<client_id>`.
- **Recall Filtering:** Recall requests MUST pass `tags=["client:<client_id>"]` and `tags_match="any_strict"`.
