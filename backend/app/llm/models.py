"""
Pydantic schemas for LLM inputs, outputs, and structured responses.
"""

from pydantic import BaseModel, Field


class ClientBriefItem(BaseModel):
    text: str
    source_interaction_ids: list[str] = Field(default_factory=list)
    source_memory_ids: list[str] = Field(default_factory=list)


class RiskFlagItem(BaseModel):
    type: str  # e.g., "communication", "billing", "scope", "timing"
    text: str
    sources: list[str] = Field(default_factory=list)


class LLMResponseSchema(BaseModel):
    draft_reply: str
    client_brief: list[ClientBriefItem] = Field(default_factory=list)
    risk_flags: list[RiskFlagItem] = Field(default_factory=list)


class LLMExecutionResult(BaseModel):
    response: LLMResponseSchema
    model_used: str
    warnings: list[str] = Field(default_factory=list)
    is_degraded: bool = False
