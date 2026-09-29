"""
FastAPI Request and Response schemas for endpoints.
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.app.core.models import AgentResponsePackage, CompareAgentResponsePackage
from backend.app.memory.models import MemoryObservation, RecalledMemory


class ClientCreateRequest(BaseModel):
    id: str
    name: str
    industry: str
    primary_contact: str
    quirks: str


class ClientResponse(BaseModel):
    id: str
    name: str
    industry: str
    primary_contact: str
    quirks: str
    created_at: str


class RespondRequest(BaseModel):
    client_id: str
    incoming_text: str
    memory_enabled: bool = True
    compare: bool = False


class RespondApiResponse(BaseModel):
    response_id: str
    package: AgentResponsePackage | CompareAgentResponsePackage
    compare: bool = False


class FeedbackRequest(BaseModel):
    response_id: str
    outcome: Literal["went_well", "pushback"]
    notes: str | None = None


class FeedbackApiResponse(BaseModel):
    status: str
    response_id: str
    outcome: str
    retained_memory_id: str | None = None


class ImportRequest(BaseModel):
    client_id: str
    text: str


class ImportApiResponse(BaseModel):
    status: str
    client_id: str
    retained_id: str
    extracted_recall: list[RecalledMemory] = Field(default_factory=list)


class ObservationsApiResponse(BaseModel):
    client_id: str
    observations: list[MemoryObservation] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    memory_backend: str
