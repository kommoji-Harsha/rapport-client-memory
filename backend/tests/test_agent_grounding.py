"""Tests for agent logic, citation grounding, new client handling, and memory toggling."""

import pytest

from backend.app.llm.agent import RapportAgentService
from backend.app.llm.models import BriefItem, LLMStructuredOutput, RiskFlag
from backend.app.memory.fake import FakeMemory


@pytest.mark.asyncio
async def test_grounding_drops_fake_citations(fake_memory: FakeMemory) -> None:
    await fake_memory.retain_interaction(
        client_id="client_a",
        interaction_id="int_real_10",
        content="Client A prefers async Slack messages and no early calls.",
        context="Preferences",
        timestamp="2024-03-01T10:00:00Z",
    )

    agent = RapportAgentService(memory_backend=fake_memory)

    fake_llm_output = LLMStructuredOutput(
        draft_reply="Draft reply text",
        client_brief=[
            BriefItem(text="Prefers async Slack", source_interaction_ids=["int_real_10", "int_fake_999"]),
        ],
        risk_flags=[
            RiskFlag(type="timing", text="Dislikes early calls", sources=["int_fake_888"]),
        ],
    )

    grounded_brief, grounded_risks = agent._ground_citations(
        raw_brief=fake_llm_output.client_brief,
        raw_risks=fake_llm_output.risk_flags,
        recalled_memories=await fake_memory.recall_client("client_a", "Slack calls"),
        is_new_client=False,
    )

    assert grounded_brief[0].source_interaction_ids == ["int_real_10"]
    assert grounded_risks[0].sources == []


@pytest.mark.asyncio
async def test_new_client_no_history(fake_memory: FakeMemory) -> None:
    agent = RapportAgentService(memory_backend=fake_memory)

    resp = await agent.generate_response(
        client_id="new_client_99",
        client_name="New Client LLC",
        incoming_text="Hello, we would like a quote for redesigning our portal.",
        memory_enabled=True,
    )

    assert resp.client_id == "new_client_99"
    assert resp.memory_used == []
    assert any("No past memory found" in w for w in resp.warnings)
    assert any("New client" in b.text for b in resp.client_brief)


@pytest.mark.asyncio
async def test_respond_memory_off(fake_memory: FakeMemory) -> None:
    await fake_memory.retain_interaction(
        client_id="client_a",
        interaction_id="int_1",
        content="Sensitive payment details",
        context="Context",
        timestamp="2024-01-01T10:00:00Z",
    )

    agent = RapportAgentService(memory_backend=fake_memory)

    resp = await agent.generate_response(
        client_id="client_a",
        client_name="Client A",
        incoming_text="Where should I send payment?",
        memory_enabled=False,
    )

    assert resp.memory_enabled is False
    assert resp.memory_used == []
