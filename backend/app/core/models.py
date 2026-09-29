"""
Core response models for agent pipeline output.
"""

from pydantic import BaseModel, Field

from backend.app.llm.models import ClientBriefItem, RiskFlagItem
from backend.app.memory.models import RecalledMemory


class AgentResponsePackage(BaseModel):
    draft_reply: str
    client_brief: list[ClientBriefItem] = Field(default_factory=list)
    risk_flags: list[RiskFlagItem] = Field(default_factory=list)
    memory_used: list[RecalledMemory] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_used: str
    is_degraded: bool = False


class CompareAgentResponsePackage(BaseModel):
    memory_on: AgentResponsePackage
    memory_off: AgentResponsePackage
