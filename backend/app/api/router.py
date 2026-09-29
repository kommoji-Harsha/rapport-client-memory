"""
FastAPI application router setup and dependency wiring.
"""

import datetime
import os
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.api.schemas import (
    ClientCreateRequest,
    ClientResponse,
    FeedbackApiResponse,
    FeedbackRequest,
    HealthResponse,
    ImportApiResponse,
    ImportRequest,
    ObservationsApiResponse,
    RespondApiResponse,
    RespondRequest,
)
from backend.app.core.models import CompareAgentResponsePackage
from backend.app.db.database import (
    ClientDBModel,
    create_or_update_client,
    get_client,
    list_clients,
    log_response,
    save_feedback,
)
from backend.app.llm.client import GroqLLMClient
from backend.app.memory.fake import FakeMemory
from backend.app.memory.hindsight import HindsightMemory
from backend.app.memory.models import RetainItem
from backend.app.memory.protocol import MemoryBackend
from backend.app.services.agent_service import RapportAgentService

api_router = APIRouter()

# Global backend instances (overridden in tests)
_memory_backend: MemoryBackend | None = None
_llm_client: GroqLLMClient | None = None
_agent_service: RapportAgentService | None = None


def get_memory_backend() -> MemoryBackend:
    global _memory_backend
    if _memory_backend is None:
        # Check if running offline test mode vs production
        if os.environ.get("USE_FAKE_MEMORY", "").lower() in ("true", "1"):
            _memory_backend = FakeMemory()
        else:
            _memory_backend = HindsightMemory()
    return _memory_backend


def get_llm_client() -> GroqLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = GroqLLMClient()
    return _llm_client


def get_agent_service() -> RapportAgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = RapportAgentService(
            memory_backend=get_memory_backend(),
            llm_client=get_llm_client(),
        )
    return _agent_service


def set_test_dependencies(
    memory_backend: MemoryBackend | None = None,
    llm_client: GroqLLMClient | None = None,
) -> None:
    """Helper to inject dependencies for testing."""
    global _memory_backend, _llm_client, _agent_service
    if memory_backend is not None:
        _memory_backend = memory_backend
    if llm_client is not None:
        _llm_client = llm_client
    _agent_service = RapportAgentService(
        memory_backend=get_memory_backend(),
        llm_client=get_llm_client(),
    )


@api_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    backend_type = get_memory_backend().__class__.__name__
    return HealthResponse(status="ok", version="0.1.0", memory_backend=backend_type)


@api_router.get("/clients", response_model=list[ClientResponse])
async def get_clients_endpoint() -> list[ClientResponse]:
    db_clients = list_clients()
    return [
        ClientResponse(
            id=c.id,
            name=c.name,
            industry=c.industry,
            primary_contact=c.primary_contact,
            quirks=c.quirks,
            created_at=c.created_at,
        )
        for c in db_clients
    ]


@api_router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client_endpoint(req: ClientCreateRequest) -> ClientResponse:
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db_model = ClientDBModel(
        id=req.id,
        name=req.name,
        industry=req.industry,
        primary_contact=req.primary_contact,
        quirks=req.quirks,
        created_at=created_at,
    )
    saved = create_or_update_client(db_model)

    # Retain profile in memory backend
    memory = get_memory_backend()
    profile_content = (
        f"Client Profile: {req.name} ({req.industry}). "
        f"Primary Contact: {req.primary_contact}. Quirks: {req.quirks}"
    )
    await memory.retain_interaction(
        client_id=req.id,
        item=RetainItem(
            content=profile_content,
            context=f"Profile creation for client {req.name}",
            document_id=f"client-profile-{req.id}",
            metadata={"client_id": req.id, "type": "client_profile"},
            tags=[f"client:{req.id}", "type:profile"],
            timestamp=created_at,
        ),
    )

    return ClientResponse(
        id=saved.id,
        name=saved.name,
        industry=saved.industry,
        primary_contact=saved.primary_contact,
        quirks=saved.quirks,
        created_at=saved.created_at,
    )


@api_router.post("/respond", response_model=RespondApiResponse)
async def respond_endpoint(req: RespondRequest) -> RespondApiResponse:
    # Input validation
    if not req.incoming_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="incoming_text cannot be empty",
        )
    if len(req.incoming_text) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="incoming_text exceeds 10,000 character limit",
        )

    client = get_client(req.client_id)
    if not client:
        # Create lightweight placeholder client entry if missing
        create_or_update_client(
            ClientDBModel(
                id=req.client_id,
                name=f"Client {req.client_id}",
                industry="Unknown",
                primary_contact="Unknown",
                quirks="No prior profile recorded.",
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )

    agent = get_agent_service()
    res_id = f"resp-{uuid.uuid4().hex[:10]}"

    if req.compare:
        compare_pkg: CompareAgentResponsePackage = await agent.compare_response(
            client_id=req.client_id,
            incoming_text=req.incoming_text,
        )
        log_response(
            client_id=req.client_id,
            incoming_text=req.incoming_text,
            memory_enabled=True,
            draft_reply=compare_pkg.memory_on.draft_reply,
            model_used=compare_pkg.memory_on.model_used,
            response_id=res_id,
        )
        return RespondApiResponse(
            response_id=res_id,
            package=compare_pkg,
            compare=True,
        )
    else:
        pkg = await agent.process_incoming_message(
            client_id=req.client_id,
            incoming_text=req.incoming_text,
            memory_enabled=req.memory_enabled,
        )
        log_response(
            client_id=req.client_id,
            incoming_text=req.incoming_text,
            memory_enabled=req.memory_enabled,
            draft_reply=pkg.draft_reply,
            model_used=pkg.model_used,
            response_id=res_id,
        )
        return RespondApiResponse(
            response_id=res_id,
            package=pkg,
            compare=False,
        )


@api_router.post("/feedback", response_model=FeedbackApiResponse)
async def feedback_endpoint(req: FeedbackRequest) -> FeedbackApiResponse:
    """Save outcome feedback idempotently and retain in memory bank."""
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    saved = save_feedback(
        response_id=req.response_id,
        outcome=req.outcome,
        notes=req.notes,
        created_at=now_str,
    )

    memory = get_memory_backend()
    # Retain feedback into memory bank for learning curve
    retained_id: str | None = None
    try:
        retained_id = await memory.retain_feedback(
            client_id="global",
            response_id=req.response_id,
            outcome=req.outcome,
            notes=req.notes,
        )
    except Exception:
        retained_id = f"feedback-{req.response_id}"

    return FeedbackApiResponse(
        status="success",
        response_id=saved.response_id,
        outcome=saved.outcome,
        retained_memory_id=retained_id,
    )


@api_router.post("/import", response_model=ImportApiResponse)
async def import_endpoint(req: ImportRequest) -> ImportApiResponse:
    """Import pasted client history into memory bank and return follow-up recall."""
    if not req.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="import text cannot be empty",
        )

    memory = get_memory_backend()
    doc_id = f"import-{uuid.uuid4().hex[:8]}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    retained_id = await memory.retain_interaction(
        client_id=req.client_id,
        item=RetainItem(
            content=req.text,
            context=f"Imported interaction history for client {req.client_id}",
            document_id=doc_id,
            metadata={"type": "import", "client_id": req.client_id},
            tags=[f"client:{req.client_id}", "type:import"],
            timestamp=now_str,
        ),
    )

    # Perform immediate follow-up recall to confirm extraction
    extracted = await memory.recall_client(
        client_id=req.client_id,
        query=req.text[:200],
        budget="mid",
    )

    return ImportApiResponse(
        status="success",
        client_id=req.client_id,
        retained_id=retained_id,
        extracted_recall=extracted,
    )


@api_router.get("/memory/observations", response_model=ObservationsApiResponse)
async def get_observations_endpoint(
    client_id: str = Query(..., description="Target client ID")
) -> ObservationsApiResponse:
    memory = get_memory_backend()
    obs = await memory.list_observations(client_id=client_id)
    return ObservationsApiResponse(
        client_id=client_id,
        observations=obs,
    )
