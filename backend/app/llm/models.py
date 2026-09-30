"""Pydantic schemas for LLM and Agent responses."""

from pydantic import BaseModel, Field

from backend.app.memory.models import RecalledMemory


class BriefItem(BaseModel):
    """Client brief entry citing source interactions or memories."""

    text: str
    source_interaction_ids: list[str] = Field(default_factory=list)
    source_memory_ids: list[str] = Field(default_factory=list)


class RiskFlag(BaseModel):
    """Identified client risk or preference watch-point."""

    type: str  # e.g., "payment", "scope", "communication", "timing"
    text: str
    sources: list[str] = Field(default_factory=list)


class LLMStructuredOutput(BaseModel):
    """Raw structured output expected from LLM JSON generation."""

    draft_reply: str
    client_brief: list[BriefItem] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Full response returned by the Rapport agent endpoint."""

    response_id: str | None = None
    client_id: str
    incoming_text: str
    memory_enabled: bool
    draft_reply: str
    client_brief: list[BriefItem] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    memory_used: list[RecalledMemory] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_used: str
