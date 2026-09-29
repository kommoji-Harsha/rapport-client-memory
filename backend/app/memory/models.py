"""
Domain models for the Rapport client-memory layer.
"""

from typing import Any

from pydantic import BaseModel, Field


class MemoryScores(BaseModel):
    final: float = 0.0
    reranker: float = 0.0
    semantic: float = 0.0
    keyword: float = 0.0


class RecalledMemory(BaseModel):
    id: str
    text: str
    type: str = "world"  # world | experience | observation
    context: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    occurred_start: str | None = None
    mentioned_at: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    source_fact_ids: list[str] = Field(default_factory=list)
    source_interaction_id: str | None = None
    scores: MemoryScores = Field(default_factory=MemoryScores)


class MemoryObservation(BaseModel):
    id: str
    text: str
    type: str = "observation"
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetainItem(BaseModel):
    content: str
    context: str
    timestamp: str | None = None
    document_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
