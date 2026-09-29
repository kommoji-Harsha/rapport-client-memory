"""
FakeMemory implementation for offline testing.
Strictly honours tag-filter semantics: any_strict excludes untagged memories
and memories with non-matching tags.
"""

import uuid
from typing import Any

from backend.app.memory.models import MemoryObservation, MemoryScores, RecalledMemory, RetainItem


class FakeMemory:
    """In-memory fake backend that strictly enforces tag-filter semantics."""

    def __init__(self) -> None:
        self.store: list[dict[str, Any]] = []
        self.should_timeout: bool = False

    async def initialize_bank(self) -> None:
        pass

    async def retain_interaction(
        self,
        client_id: str,
        item: RetainItem,
    ) -> str:
        client_tag = f"client:{client_id}"
        tags = list(item.tags)
        if client_tag not in tags:
            tags.append(client_tag)

        meta = dict(item.metadata)
        meta["client_id"] = client_id

        mem_id = f"fake-mem-{uuid.uuid4().hex[:8]}"
        doc_id = item.document_id or f"doc-{uuid.uuid4().hex[:8]}"

        source_interaction_id: str | None = None
        if doc_id.startswith("interaction-"):
            source_interaction_id = doc_id.replace("interaction-", "")
        elif "interaction_id" in meta:
            source_interaction_id = str(meta["interaction_id"])

        record = {
            "id": mem_id,
            "text": item.content,
            "type": "world",
            "context": item.context,
            "metadata": meta,
            "tags": tags,
            "entities": [],
            "occurred_start": item.timestamp,
            "mentioned_at": item.timestamp,
            "document_id": doc_id,
            "chunk_id": f"chunk-{mem_id}",
            "source_fact_ids": [f"fact-{mem_id}"],
            "source_interaction_id": source_interaction_id,
            "scores": MemoryScores(final=0.9, reranker=0.85, semantic=0.88, keyword=0.8),
        }
        self.store.append(record)
        return mem_id

    async def retain_feedback(
        self,
        client_id: str,
        response_id: str,
        outcome: str,
        notes: str | None = None,
    ) -> str:
        content = f"Feedback outcome: {outcome}. Response ID: {response_id}."
        if notes:
            content += f" Additional Notes: {notes}"

        doc_id = f"feedback-{response_id}"
        tags = [f"client:{client_id}", "type:feedback", f"outcome:{outcome}"]
        item = RetainItem(
            content=content,
            context=f"User feedback on response {response_id}",
            document_id=doc_id,
            metadata={"response_id": response_id, "outcome": outcome},
            tags=tags,
        )
        return await self.retain_interaction(client_id, item)

    async def recall_client(
        self,
        client_id: str,
        query: str,
        budget: str = "mid",
        max_tokens: int = 4096,
    ) -> list[RecalledMemory]:
        if self.should_timeout:
            raise TimeoutError("Hindsight memory request timed out")

        client_tag = f"client:{client_id}"
        recalled: list[RecalledMemory] = []

        # STRICT TAG MATCHING: any_strict excludes untagged memories and non-matching tags
        for record in self.store:
            record_tags = record.get("tags", [])
            if not record_tags or client_tag not in record_tags:
                # Exclude untagged or non-matching client tag
                continue

            # Check query keyword relevance if query provided
            query_terms = [t.lower() for t in query.split() if len(t) > 2]
            record_text = record["text"].lower()

            broad_query = any(k in query.lower() for k in ("preference", "all", "history"))
            is_match = not query_terms or broad_query or any(t in record_text for t in query_terms)

            if is_match:
                recalled.append(
                    RecalledMemory(
                        id=record["id"],
                        text=record["text"],
                        type=record["type"],
                        context=record["context"],
                        metadata=record["metadata"],
                        tags=record["tags"],
                        entities=record["entities"],
                        occurred_start=record["occurred_start"],
                        mentioned_at=record["mentioned_at"],
                        document_id=record["document_id"],
                        chunk_id=record["chunk_id"],
                        source_fact_ids=record["source_fact_ids"],
                        source_interaction_id=record["source_interaction_id"],
                        scores=record["scores"],
                    )
                )

        return recalled

    async def list_observations(
        self,
        client_id: str,
    ) -> list[MemoryObservation]:
        if self.should_timeout:
            raise TimeoutError("Hindsight memory request timed out")

        client_tag = f"client:{client_id}"
        obs_list: list[MemoryObservation] = []

        for record in self.store:
            record_tags = record.get("tags", [])
            if client_tag in record_tags:
                if record["type"] == "observation" or "type:profile" in record_tags:
                    obs_list.append(
                        MemoryObservation(
                            id=record["id"],
                            text=record["text"],
                            type="observation",
                            tags=record_tags,
                            metadata=record["metadata"],
                        )
                    )

        return obs_list

    async def close(self) -> None:
        pass
