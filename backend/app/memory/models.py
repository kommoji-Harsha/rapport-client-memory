"""Pydantic models for memory representations."""

from typing import Any

from pydantic import BaseModel, Field


class RecalledMemory(BaseModel):
    """Typed recall item with all required Hindsight fields and derived source_interaction_id."""

    id: str
    text: str
    type: str  # "world", "experience", or "observation"
    context: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    entities: list[Any] = Field(default_factory=list)
    occurred_start: str | None = None
    mentioned_at: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    source_fact_ids: list[str] = Field(default_factory=list)
    scores: dict[str, float | None] = Field(default_factory=dict)
    source_interaction_id: str | None = None


class ObservationItem(BaseModel):
    """Typed observation item for a client."""

    id: str
    text: str
    context: str | None = None
    client_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
