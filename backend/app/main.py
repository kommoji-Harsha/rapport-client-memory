"""FastAPI application for Rapport client-memory agent backend."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.db import Database
from backend.app.llm.agent import RapportAgentService
from backend.app.memory.hindsight_memory import HindsightMemory
from backend.app.memory.protocol import MemoryBackend

# Database setup
db = Database()


def get_memory_backend() -> MemoryBackend:
    """Instantiate HindsightMemory for production application."""
    return HindsightMemory()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Lifespan startup
    seed_path = Path(__file__).resolve().parent.parent.parent / "data" / "clients.json"
    db.init_db(clients_seed_path=seed_path)

    if not getattr(app.state, "memory", None):
        memory = get_memory_backend()
        await memory.bootstrap_bank()
        app.state.memory = memory

    if not getattr(app.state, "agent", None):
        app.state.agent = RapportAgentService(memory_backend=app.state.memory)

    yield

    # Lifespan shutdown
    if hasattr(app.state, "memory"):
        await app.state.memory.close()


app = FastAPI(
    title="Rapport Client-Memory API",
    version="0.1.0",
    description="Backend API for Rapport client-memory agent for freelancers",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Schemas
class ClientCreateRequest(BaseModel):
    id: str | None = None
    name: str
    contact_name: str = ""
    contact_email: str = ""
    industry: str = ""
    primary_quirk: str = ""


class RespondRequest(BaseModel):
    client_id: str
    incoming_text: str
    memory_enabled: bool = True
    compare: bool = False


class FeedbackRequest(BaseModel):
    response_id: str
    outcome: Literal["went_well", "pushback"]
    notes: str | None = None


class ImportRequest(BaseModel):
    client_id: str
    text: str


# Endpoints
@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    memory_type = type(app.state.memory).__name__ if hasattr(app.state, "memory") else "Unknown"
    return {
        "status": "ok",
        "version": "0.1.0",
        "memory_backend": memory_type,
    }


@app.get("/api/clients")
async def list_clients() -> list[dict[str, Any]]:
    return db.get_clients()


@app.post("/api/clients", status_code=201)
async def create_client(req: ClientCreateRequest) -> dict[str, Any]:
    client_id = req.id or f"c_{req.name.lower().replace(' ', '_')}"
    existing = db.get_client(client_id)
    if existing:
        return existing
    return db.create_client(
        client_id=client_id,
        name=req.name,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        industry=req.industry,
        primary_quirk=req.primary_quirk,
    )


@app.post("/api/respond")
async def respond(req: RespondRequest) -> Any:
    if not req.incoming_text.strip():
        raise HTTPException(status_code=400, detail="incoming_text cannot be empty")

    client = db.get_client(req.client_id)
    client_name = client["name"] if client else f"Client {req.client_id}"

    agent: RapportAgentService = app.state.agent

    if req.compare:
        comparison = await agent.compare_responses(
            client_id=req.client_id,
            client_name=client_name,
            incoming_text=req.incoming_text,
        )
        db.save_response(comparison["memory_on"].model_dump())
        db.save_response(comparison["memory_off"].model_dump())
        return comparison

    agent_resp = await agent.generate_response(
        client_id=req.client_id,
        client_name=client_name,
        incoming_text=req.incoming_text,
        memory_enabled=req.memory_enabled,
    )
    db.save_response(agent_resp.model_dump())
    return agent_resp


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest) -> dict[str, Any]:
    resp_record = db.get_response(req.response_id)
    client_id = resp_record["client_id"] if resp_record else "unknown"

    memory: MemoryBackend = app.state.memory
    await memory.retain_feedback(
        client_id=client_id,
        response_id=req.response_id,
        outcome=req.outcome,
        notes=req.notes,
    )

    saved = db.save_feedback(
        response_id=req.response_id,
        client_id=client_id,
        outcome=req.outcome,
        notes=req.notes,
    )
    return {"status": "success", "feedback": saved}


@app.post("/api/import")
async def import_history(req: ImportRequest) -> dict[str, Any]:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Import text cannot be empty")

    import_id = f"import_{os.urandom(4).hex()}"
    memory: MemoryBackend = app.state.memory
    now_iso = datetime.now(UTC).isoformat()

    await memory.retain_interaction(
        client_id=req.client_id,
        interaction_id=import_id,
        content=req.text,
        context="Imported client interaction history",
        timestamp=now_iso,
    )

    recalled = await memory.recall_client(
        client_id=req.client_id,
        query=req.text[:200],
    )

    return {
        "status": "imported",
        "client_id": req.client_id,
        "import_id": import_id,
        "recalled_extracted": [m.model_dump() for m in recalled],
    }


@app.get("/api/memory/observations")
async def get_observations(client_id: str = Query(..., description="Client ID to filter observations")) -> list[dict[str, Any]]:
    memory: MemoryBackend = app.state.memory
    obs_list = await memory.list_observations(client_id=client_id)
    return [obs.model_dump() for obs in obs_list]
