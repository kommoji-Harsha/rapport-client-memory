"""
Tests for grounding validation, LLM retries, fallback models, and memory timeouts.
"""

import pytest

from backend.app.core.grounding import validate_and_filter_grounding
from backend.app.llm.client import GroqLLMClient
from backend.app.llm.models import ClientBriefItem, LLMResponseSchema, RiskFlagItem
from backend.app.memory.fake import FakeMemory
from backend.app.memory.models import MemoryScores, RecalledMemory
from backend.app.services.agent_service import RapportAgentService


def test_grounding_drops_hallucinated_citations() -> None:
    recalled = [
        RecalledMemory(
            id="mem-101",
            text="Client prefers email.",
            source_interaction_id="int-c1-01",
            document_id="interaction-int-c1-01",
            scores=MemoryScores(final=0.9),
        )
    ]

    # LLM schema containing valid citation 'int-c1-01' and fake citations 'fake-999' / 'fake-888'
    unfiltered_schema = LLMResponseSchema(
        draft_reply="I will email you.",
        client_brief=[
            ClientBriefItem(
                text="Prefers email channel.",
                source_interaction_ids=["int-c1-01", "fake-999"],
                source_memory_ids=["mem-101", "fake-888"],
            )
        ],
        risk_flags=[
            RiskFlagItem(
                type="communication",
                text="Communication channel preference",
                sources=["int-c1-01", "fake-999"],
            )
        ],
    )

    filtered = validate_and_filter_grounding(unfiltered_schema, recalled)

    # Hallucinated citations dropped
    assert filtered.client_brief[0].source_interaction_ids == ["int-c1-01"]
    assert filtered.client_brief[0].source_memory_ids == ["mem-101"]
    assert filtered.risk_flags[0].sources == ["int-c1-01"]


@pytest.mark.asyncio
async def test_memory_timeout_degrades_gracefully_without_crashing() -> None:
    fake_memory = FakeMemory()
    fake_memory.should_timeout = True  # Simulate timeout failure

    llm_client = GroqLLMClient(api_key="")  # Uses degraded response assembly
    service = RapportAgentService(memory_backend=fake_memory, llm_client=llm_client)

    # Must NOT crash on timeout; returns degraded draft with warning
    result = await service.process_incoming_message(
        client_id="c1",
        incoming_text="Can we discuss the invoice?",
        memory_enabled=True,
    )

    assert result.draft_reply is not None
    assert any("timed out" in w.lower() or "failed" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_new_client_without_history() -> None:
    fake_memory = FakeMemory()
    llm_client = GroqLLMClient(api_key="")
    service = RapportAgentService(memory_backend=fake_memory, llm_client=llm_client)

    result = await service.process_incoming_message(
        client_id="brand-new-client",
        incoming_text="Hello, I am interested in your consulting services.",
        memory_enabled=True,
    )

    assert result.draft_reply is not None
    assert len(result.memory_used) == 0
