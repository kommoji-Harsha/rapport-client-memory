"""MemoryBackend Protocol definition."""

from typing import Any, Protocol, runtime_checkable

from backend.app.memory.models import ObservationItem, RecalledMemory


@runtime_checkable
class MemoryBackend(Protocol):
    """Protocol for agent memory operations."""

    async def bootstrap_bank(self) -> None:
        """Ensure the memory bank is created with proper mission/disposition."""
        ...

    async def retain_interaction(
        self,
        client_id: str,
        interaction_id: str,
        content: str,
        context: str,
        timestamp: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Retain a single client interaction into memory."""
        ...

    async def retain_batch_interactions(
        self,
        items: list[dict[str, Any]],
    ) -> None:
        """Batch retain multiple interactions or memories."""
        ...

    async def retain_feedback(
        self,
        client_id: str,
        response_id: str,
        outcome: str,  # "went_well" or "pushback"
        notes: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Retain user feedback on a draft response."""
        ...

    async def recall_client(
        self,
        client_id: str,
        query: str,
        budget: str = "mid",
    ) -> list[RecalledMemory]:
        """Recall relevant memories strictly scoped to client_id using tag filtering."""
        ...

    async def list_observations(
        self,
        client_id: str,
    ) -> list[ObservationItem]:
        """Retrieve observations scoped to a client."""
        ...

    async def close(self) -> None:
        """Close client connections/resources."""
        ...
