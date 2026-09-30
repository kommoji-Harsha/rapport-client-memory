"""FakeMemory implementation for offline testing."""

import uuid
from datetime import UTC, datetime
from typing import Any

from backend.app.memory.models import ObservationItem, RecalledMemory


class FakeMemory:
    """In-memory FakeMemory implementing MemoryBackend for offline tests.

    Strictly honours tag-filter semantics ('any_strict' excludes untagged memories
    or memories tagged for other clients).
    """

    def __init__(self, bank_id: str = "test-bank") -> None:
        self.bank_id = bank_id
        # Stores memory records: dict with keys: id, text, type, context, metadata, tags, entities, occurred_start, mentioned_at, document_id, chunk_id, source_fact_ids, scores
        self._memories: list[dict[str, Any]] = []
        # Store feedback items by response_id to enforce idempotency
        self._feedback_store: dict[str, dict[str, Any]] = {}
        self.bank_bootstrapped = False

    async def bootstrap_bank(self) -> None:
        self.bank_bootstrapped = True

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
        client_tag = f"client:{client_id}"
        all_tags = list(tags) if tags else []
        if client_tag not in all_tags:
            all_tags.append(client_tag)

        meta = dict(metadata or {})
        meta["client_id"] = client_id
        meta["interaction_id"] = interaction_id

        doc_id = f"interaction:{interaction_id}"
        mem_id = f"mem-{uuid.uuid4().hex[:8]}"

        item = {
            "id": mem_id,
            "text": content,
            "type": "experience",
            "context": context,
            "metadata": meta,
            "tags": all_tags,
            "entities": [],
            "occurred_start": timestamp,
            "mentioned_at": timestamp,
            "document_id": doc_id,
            "chunk_id": f"chunk-{mem_id}",
            "source_fact_ids": [f"fact-{mem_id}"],
            "scores": {"final": 0.9, "reranker": 0.9, "semantic": 0.85, "keyword": 0.8},
        }
        self._memories.append(item)

    async def retain_batch_interactions(
        self,
        items: list[dict[str, Any]],
    ) -> None:
        for raw_item in items:
            client_id = raw_item.get("client_id")
            metadata = raw_item.get("metadata", {})
            if not client_id and "client_id" in metadata:
                client_id = metadata["client_id"]

            tags = raw_item.get("tags", [])
            if client_id:
                client_tag = f"client:{client_id}"
                if client_tag not in tags:
                    tags = list(tags) + [client_tag]

            doc_id = raw_item.get("document_id") or raw_item.get("id") or f"doc-{uuid.uuid4().hex[:8]}"
            interaction_id = metadata.get("interaction_id")
            if not interaction_id and doc_id and doc_id.startswith("interaction:"):
                interaction_id = doc_id.replace("interaction:", "")

            meta = dict(metadata)
            if client_id:
                meta["client_id"] = client_id
            if interaction_id:
                meta["interaction_id"] = interaction_id

            timestamp = raw_item.get("timestamp") or raw_item.get("occurred_start") or datetime.now(UTC).isoformat()
            content = raw_item.get("content") or raw_item.get("text", "")
            context = raw_item.get("context", "")
            mem_type = raw_item.get("type", "experience")

            mem_id = f"mem-{uuid.uuid4().hex[:8]}"
            item = {
                "id": mem_id,
                "text": content,
                "type": mem_type,
                "context": context,
                "metadata": meta,
                "tags": tags,
                "entities": [],
                "occurred_start": timestamp,
                "mentioned_at": timestamp,
                "document_id": doc_id,
                "chunk_id": f"chunk-{mem_id}",
                "source_fact_ids": [f"fact-{mem_id}"],
                "scores": {"final": 0.9, "reranker": 0.9, "semantic": 0.85, "keyword": 0.8},
            }
            self._memories.append(item)

    async def retain_feedback(
        self,
        client_id: str,
        response_id: str,
        outcome: str,
        notes: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        ts = timestamp or datetime.now(UTC).isoformat()
        feedback_text = f"Feedback on draft response {response_id}: outcome={outcome}."
        if notes:
            feedback_text += f" Notes: {notes}"

        client_tag = f"client:{client_id}"
        tags = [client_tag, "type:feedback", f"outcome:{outcome}"]
        doc_id = f"feedback:{response_id}"

        fb_entry = {
            "id": f"fb-{response_id}",
            "text": feedback_text,
            "type": "experience",
            "context": f"User feedback outcome: {outcome}",
            "metadata": {
                "client_id": client_id,
                "response_id": response_id,
                "outcome": outcome,
                "notes": notes or "",
            },
            "tags": tags,
            "entities": [],
            "occurred_start": ts,
            "mentioned_at": ts,
            "document_id": doc_id,
            "chunk_id": f"chunk-fb-{response_id}",
            "source_fact_ids": [f"fact-fb-{response_id}"],
            "scores": {"final": 0.95, "reranker": 0.95, "semantic": 0.9, "keyword": 0.9},
        }

        # Idempotent storage
        self._feedback_store[response_id] = fb_entry

        # Update in memories list if exists, else append
        existing_idx = None
        for idx, mem in enumerate(self._memories):
            if mem.get("document_id") == doc_id:
                existing_idx = idx
                break

        if existing_idx is not None:
            self._memories[existing_idx] = fb_entry
        else:
            self._memories.append(fb_entry)

    async def recall_client(
        self,
        client_id: str,
        query: str,
        budget: str = "mid",
    ) -> list[RecalledMemory]:
        """Recall memories with strict 'any_strict' tag matching semantics.

        In 'any_strict' with tags=['client:<client_id>'], ANY memory item that does NOT
        have 'client:<client_id>' in its tags list is STRICTLY EXCLUDED.
        Untagged items or items tagged for other clients are completely filtered out.
        """
        required_tag = f"client:{client_id}"
        matching_items: list[dict[str, Any]] = []

        query_words = set(query.lower().split()) if query else set()

        for mem in self._memories:
            tags = mem.get("tags") or []
            # strict tag match requirement:
            if required_tag not in tags:
                continue

            # Calculate a simple keyword similarity score for ranking
            text_words = set(mem.get("text", "").lower().split())
            context_words = set(mem.get("context", "").lower().split()) if mem.get("context") else set()
            combined = text_words | context_words

            overlap = len(query_words & combined) if query_words else 1
            # Give higher base score to match query, but always include client memories if overlap or broad query
            score = 0.5 + (0.1 * min(overlap, 5))

            item_copy = dict(mem)
            item_copy["scores"] = {
                "final": round(score, 3),
                "reranker": round(score, 3),
                "semantic": round(score * 0.9, 3),
                "keyword": round(score * 0.8, 3),
            }
            matching_items.append(item_copy)

        # Sort by final score descending
        matching_items.sort(key=lambda x: x["scores"]["final"], reverse=True)

        results: list[RecalledMemory] = []
        for item in matching_items:
            doc_id = item.get("document_id")
            meta = item.get("metadata", {})
            source_int_id = meta.get("interaction_id")
            if not source_int_id and doc_id and doc_id.startswith("interaction:"):
                source_int_id = doc_id.replace("interaction:", "")

            results.append(
                RecalledMemory(
                    id=item["id"],
                    text=item["text"],
                    type=item["type"],
                    context=item.get("context"),
                    metadata=meta,
                    tags=item.get("tags", []),
                    entities=item.get("entities", []),
                    occurred_start=item.get("occurred_start"),
                    mentioned_at=item.get("mentioned_at"),
                    document_id=doc_id,
                    chunk_id=item.get("chunk_id"),
                    source_fact_ids=item.get("source_fact_ids", []),
                    scores=item.get("scores", {}),
                    source_interaction_id=source_int_id,
                )
            )

        return results

    async def list_observations(
        self,
        client_id: str,
    ) -> list[ObservationItem]:
        required_tag = f"client:{client_id}"
        obs_items: list[ObservationItem] = []

        for mem in self._memories:
            tags = mem.get("tags") or []
            if required_tag not in tags:
                continue

            if mem.get("type") == "observation" or "observation" in tags:
                obs_items.append(
                    ObservationItem(
                        id=mem["id"],
                        text=mem["text"],
                        context=mem.get("context"),
                        client_id=client_id,
                        metadata=mem.get("metadata", {}),
                    )
                )

        return obs_items

    async def close(self) -> None:
        pass
