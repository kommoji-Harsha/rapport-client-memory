"""Contract test verifying RecallScores extraction in HindsightMemory.recall_client."""

from unittest.mock import AsyncMock, patch

import pytest
from hindsight_client import RecallResponse, RecallResult
from hindsight_client_api.models.recall_scores import RecallScores

from backend.app.memory.hindsight_memory import HindsightMemory


@pytest.mark.asyncio
async def test_recall_client_scores_object_mapping() -> None:
    # Build real RecallScores object with keyword=None
    real_scores = RecallScores(
        final=0.95,
        reranker=0.92,
        semantic=0.88,
        keyword=None,
    )

    real_result = RecallResult(
        id="mem-scores-123",
        text="Client prefers async Slack updates",
        type="experience",
        context="Communication preference",
        metadata={"client_id": "client_test", "interaction_id": "int_999"},
        tags=["client:client_test"],
        document_id="interaction:int_999",
        scores=real_scores,
    )

    mock_response = RecallResponse(results=[real_result])

    memory = HindsightMemory(bank_id="test-bank", api_key="dummy_key")

    with patch.object(memory.client, "arecall", new_callable=AsyncMock) as mock_arecall:
        mock_arecall.return_value = mock_response

        recalled = await memory.recall_client(client_id="client_test", query="Slack updates")

        assert len(recalled) == 1
        item = recalled[0]
        assert item.id == "mem-scores-123"
        assert item.source_interaction_id == "int_999"
        assert item.scores == {
            "final": 0.95,
            "reranker": 0.92,
            "semantic": 0.88,
            "keyword": None,
        }
