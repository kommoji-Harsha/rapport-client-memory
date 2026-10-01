"""Tests for LLM retry, fallback model execution, and degraded responses."""

from unittest.mock import patch

import pytest

from backend.app.llm.client import GroqLLMClient
from backend.app.llm.models import BriefItem, LLMStructuredOutput
from backend.app.memory.models import RecalledMemory


@pytest.mark.asyncio
async def test_groq_llm_client_degraded_fallback_without_api_key() -> None:
    client = GroqLLMClient(api_key="")

    memories = [
        RecalledMemory(
            id="mem-1",
            text="Client pays invoices 20 days late",
            type="experience",
            source_interaction_id="int_008",
        )
    ]

    output, model_used, warnings = await client.generate(
        system_prompt="system",
        user_prompt="user message",
        recalled_memories=memories,
    )

    assert model_used == "degraded_fallback"
    assert "Groq API key not configured" in warnings[0]
    assert len(output.risk_flags) > 0
    assert output.risk_flags[0].type == "payment"
    assert output.risk_flags[0].sources == ["int_008"]


@pytest.mark.asyncio
async def test_llm_fallback_model_on_primary_failure() -> None:
    client = GroqLLMClient(
        api_key="mock_key",
        primary_model="primary-mock",
        fallback_model="fallback-mock",
        max_retries_per_model=2,
    )

    async def mock_call(model: str, system_prompt: str, user_prompt: str) -> LLMStructuredOutput:
        if model == "primary-mock":
            raise RuntimeError("Primary model rate limit error 429")
        return LLMStructuredOutput(
            draft_reply="Fallback draft reply",
            client_brief=[BriefItem(text="Fallback brief item", source_interaction_ids=[], source_memory_ids=[])],
        )

    with patch.object(client, "_call_with_retries", side_effect=mock_call):
        output, model_used, warnings = await client.generate("sys", "user")

        assert model_used == "fallback-mock"
        assert output.draft_reply == "Fallback draft reply"
        assert any("Primary model primary-mock failed" in w for w in warnings)
