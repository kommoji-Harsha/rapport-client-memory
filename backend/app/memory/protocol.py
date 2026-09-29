"""
MemoryBackend protocol definition for persistent client memory.
"""

from typing import Protocol, runtime_checkable

from backend.app.memory.models import MemoryObservation, RecalledMemory, RetainItem


@runtime_checkable
class MemoryBackend(Protocol):
    """Protocol defining the memory storage and recall operations."""

    async def initialize_bank(self) -> None:
        """Ensure bank exists with proper mission and settings."""
        ...

    async def retain_interaction(
        self,
        client_id: str,
        item: RetainItem,
    ) -> str:
        """Retain a client interaction item with client:<client_id> tag isolation."""
        ...

    async def retain_feedback(
        self,
        client_id: str,
        response_id: str,
        outcome: str,  # went_well | pushback
        notes: str | None = None,
    ) -> str:
        """Retain user feedback on a draft reply to improve future responses."""
        ...

    async def recall_client(
        self,
        client_id: str,
        query: str,
        budget: str = "mid",
        max_tokens: int = 4096,
    ) -> list[RecalledMemory]:
        """Recall relevant client history using strict tag matching (tags_match='any_strict')."""
        ...

    async def list_observations(
        self,
        client_id: str,
    ) -> list[MemoryObservation]:
        """List observations/mental model items consolidated for a client."""
        ...

    async def close(self) -> None:
        """Close connection resources if applicable."""
        ...
