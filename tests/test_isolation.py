"""
Tests for strict client tag isolation and prevention of cross-client data leakage.
"""

import pytest

from backend.app.memory.fake import FakeMemory
from backend.app.memory.models import RetainItem


@pytest.mark.asyncio
async def test_cross_client_tag_isolation() -> None:
    fake_memory = FakeMemory()

    # Retain memory for Client A
    await fake_memory.retain_interaction(
        client_id="client_a",
        item=RetainItem(
            content="Client A secret project codename: ALPHA_PROJECT.",
            context="Confidential project details for Client A",
            document_id="interaction-int-a1",
            tags=["client:client_a"],
        ),
    )

    # Retain memory for Client B
    await fake_memory.retain_interaction(
        client_id="client_b",
        item=RetainItem(
            content="Client B secret project codename: BETA_PROJECT.",
            context="Confidential project details for Client B",
            document_id="interaction-int-b1",
            tags=["client:client_b"],
        ),
    )

    # Recall for Client A with tags_match='any_strict'
    recalled_a = await fake_memory.recall_client(
        client_id="client_a",
        query="project details codename",
    )

    # Verify Client A memories retrieved
    assert len(recalled_a) == 1
    assert "ALPHA_PROJECT" in recalled_a[0].text

    # CRITICAL CHECK: Verify Client B memory NEVER appears in Client A recall
    for mem in recalled_a:
        assert "BETA_PROJECT" not in mem.text
        assert "client:client_b" not in mem.tags

    # Recall for Client B
    recalled_b = await fake_memory.recall_client(
        client_id="client_b",
        query="project details codename",
    )
    assert len(recalled_b) == 1
    assert "BETA_PROJECT" in recalled_b[0].text
    for mem in recalled_b:
        assert "ALPHA_PROJECT" not in mem.text
        assert "client:client_a" not in mem.tags


@pytest.mark.asyncio
async def test_untagged_memories_excluded_by_any_strict() -> None:
    fake_memory = FakeMemory()

    # Direct insertion of an untagged memory
    fake_memory.store.append(
        {
            "id": "untagged-1",
            "text": "Untagged rogue memory data.",
            "type": "world",
            "context": "No client tag",
            "metadata": {},
            "tags": [],
            "document_id": "doc-untagged",
            "source_interaction_id": None,
            "scores": None,
        }
    )

    recalled = await fake_memory.recall_client(
        client_id="client_a",
        query="rogue memory data",
    )

    # Untagged memory must be excluded under any_strict semantics
    assert len(recalled) == 0
