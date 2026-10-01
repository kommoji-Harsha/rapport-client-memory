"""Tests for cross-client memory isolation and FakeMemory tag filtering."""

import pytest

from backend.app.memory.fake import FakeMemory


@pytest.mark.asyncio
async def test_cross_client_memory_isolation(fake_memory: FakeMemory) -> None:
    await fake_memory.retain_interaction(
        client_id="client_a",
        interaction_id="int_a_100",
        content="Client A top secret project alpha approval",
        context="Alpha approval",
        timestamp="2024-05-01T10:00:00Z",
    )

    await fake_memory.retain_interaction(
        client_id="client_b",
        interaction_id="int_b_200",
        content="Client B confidential payment terms and discount 20%",
        context="Payment terms",
        timestamp="2024-05-01T10:00:00Z",
    )

    recalled_a = await fake_memory.recall_client(client_id="client_a", query="secret project alpha payment terms")
    texts_a = [m.text for m in recalled_a]

    assert len(recalled_a) == 1
    assert "Client A top secret" in texts_a[0]
    assert not any("Client B" in text for text in texts_a)

    recalled_b = await fake_memory.recall_client(client_id="client_b", query="secret project alpha payment terms")
    texts_b = [m.text for m in recalled_b]

    assert len(recalled_b) == 1
    assert "Client B confidential" in texts_b[0]
    assert not any("Client A" in text for text in texts_b)


@pytest.mark.asyncio
async def test_any_strict_tag_matching_excludes_untagged_and_other_tags(fake_memory: FakeMemory) -> None:
    fake_memory._memories.append({
        "id": "mem-untagged",
        "text": "Global untagged company policy",
        "type": "world",
        "tags": [],
    })

    await fake_memory.retain_interaction(
        client_id="client_x",
        interaction_id="int_x_1",
        content="Client X specific preference",
        context="Preference",
        timestamp="2024-06-01T10:00:00Z",
    )

    recalled = await fake_memory.recall_client(client_id="client_x", query="company policy preference")
    recalled_ids = [m.id for m in recalled]

    assert "mem-untagged" not in recalled_ids
    assert len(recalled) == 1
    assert recalled[0].text == "Client X specific preference"
