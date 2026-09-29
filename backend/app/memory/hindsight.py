"""
HindsightMemory implementation of MemoryBackend protocol using official hindsight-client SDK.
"""

import os
from typing import Any, cast

from hindsight_client import Hindsight

from backend.app.memory.models import MemoryObservation, MemoryScores, RecalledMemory, RetainItem


class HindsightMemory:
    """Production memory backend backed by Hindsight Cloud API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        bank_id: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url or os.environ.get(
            "HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"
        )
        self.api_key = api_key or os.environ.get("HINDSIGHT_API_KEY", "")
        self.bank_id = bank_id or os.environ.get(
            "HINDSIGHT_BANK_ID", "rapport-freelancer-memory"
        )
        self.timeout = timeout
        self._client = Hindsight(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    async def initialize_bank(self) -> None:
        """Create or ensure bank with freelancer client-relationship mission."""
        try:
            await self._client.acreate_bank(
                bank_id=self.bank_id,
                name="Rapport Client Memory Bank",
                mission=(
                    "Maintain accurate, isolated client interaction histories, "
                    "communication preferences, billing patterns, decision-maker hierarchies, "
                    "and scope boundaries for freelancer consulting engagements."
                ),
                enable_observations=True,
            )
        except Exception:
            # Bank may already exist or error will be handled on operational calls
            pass

    async def retain_interaction(
        self,
        client_id: str,
        item: RetainItem,
    ) -> str:
        """Retain item tagged client:<client_id>."""
        client_tag = f"client:{client_id}"
        tags = list(item.tags)
        if client_tag not in tags:
            tags.append(client_tag)

        meta = dict(item.metadata)
        meta["client_id"] = client_id

        res = await self._client.aretain(
            bank_id=self.bank_id,
            content=item.content,
            context=item.context,
            document_id=item.document_id,
            metadata=meta,
            tags=tags,
        )
        return str(getattr(res, "id", "retained"))

    async def retain_feedback(
        self,
        client_id: str,
        response_id: str,
        outcome: str,
        notes: str | None = None,
    ) -> str:
        """Retain feedback on a draft response."""
        content = f"Feedback outcome: {outcome}. Response ID: {response_id}."
        if notes:
            content += f" Additional Notes: {notes}"

        doc_id = f"feedback-{response_id}"
        tags = [f"client:{client_id}", "type:feedback", f"outcome:{outcome}"]
        context = f"User feedback on draft response {response_id} for client {client_id}"

        res = await self._client.aretain(
            bank_id=self.bank_id,
            content=content,
            context=context,
            document_id=doc_id,
            metadata={
                "client_id": client_id,
                "response_id": response_id,
                "outcome": outcome,
                "type": "feedback",
            },
            tags=tags,
        )
        return str(getattr(res, "id", doc_id))

    async def recall_client(
        self,
        client_id: str,
        query: str,
        budget: str = "mid",
        max_tokens: int = 4096,
    ) -> list[RecalledMemory]:
        """Recall memories for client_id with tags_match='any_strict'."""
        client_tag = f"client:{client_id}"
        resp = await self._client.arecall(
            bank_id=self.bank_id,
            query=query,
            tags=[client_tag],
            tags_match="any_strict",
            budget=budget,
            max_tokens=max_tokens,
            prefer_observations=True,
        )

        results_list = getattr(resp, "results", []) or []
        memories: list[RecalledMemory] = []

        for r in results_list:
            mem_id = getattr(r, "id", "")
            text = getattr(r, "text", "")
            mem_type = getattr(r, "type", "world") or "world"
            context = getattr(r, "context", None)
            metadata = getattr(r, "metadata", {}) or {}
            tags = getattr(r, "tags", []) or []
            entities = getattr(r, "entities", []) or []
            occurred_start = getattr(r, "occurred_start", None)
            mentioned_at = getattr(r, "mentioned_at", None)
            document_id = getattr(r, "document_id", None)
            chunk_id = getattr(r, "chunk_id", None)
            source_fact_ids = getattr(r, "source_fact_ids", []) or []

            # Derive source_interaction_id from document_id or metadata
            source_interaction_id: str | None = None
            if document_id and document_id.startswith("interaction-"):
                source_interaction_id = document_id.replace("interaction-", "")
            elif "interaction_id" in metadata:
                source_interaction_id = str(metadata["interaction_id"])

            scores_obj = getattr(r, "scores", None)
            scores = MemoryScores(
                final=getattr(scores_obj, "final", 0.0) if scores_obj else 0.0,
                reranker=getattr(scores_obj, "reranker", 0.0) if scores_obj else 0.0,
                semantic=getattr(scores_obj, "semantic", 0.0) if scores_obj else 0.0,
                keyword=getattr(scores_obj, "keyword", 0.0) if scores_obj else 0.0,
            )

            memories.append(
                RecalledMemory(
                    id=mem_id,
                    text=text,
                    type=mem_type,
                    context=context,
                    metadata=metadata,
                    tags=tags,
                    entities=entities,
                    occurred_start=occurred_start,
                    mentioned_at=mentioned_at,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    source_fact_ids=source_fact_ids,
                    source_interaction_id=source_interaction_id,
                    scores=scores,
                )
            )

        return memories

    async def list_observations(
        self,
        client_id: str,
    ) -> list[MemoryObservation]:
        """List observations/mental models for client_id."""
        client_tag = f"client:{client_id}"

        # First try recall with prefer_observations
        recalled = await self.recall_client(
            client_id=client_id,
            query="client preferences communication billing guidelines observations",
            budget="mid",
        )
        obs_list = [
            MemoryObservation(
                id=m.id,
                text=m.text,
                type=m.type,
                tags=m.tags,
                entities=m.entities,
                metadata=m.metadata,
            )
            for m in recalled
            if m.type == "observation" or "observation" in m.tags
        ]

        if not obs_list:
            # Fallback: query mental models endpoint if supported
            try:
                models_resp = await self._client.alist_mental_models(bank_id=self.bank_id)
                items = getattr(models_resp, "mental_models", []) or []
                for item in items:
                    tags = getattr(item, "tags", []) or []
                    if client_tag in tags or not tags:
                        obs_list.append(
                            MemoryObservation(
                                id=getattr(item, "id", "obs"),
                                text=getattr(item, "name", "") or getattr(item, "summary", ""),
                                type="observation",
                                tags=tags,
                                metadata={},
                            )
                        )
            except Exception:
                pass

        return obs_list

    async def close(self) -> None:
        """Close hindsight client."""
        close_fn = getattr(self._client, "aclose", None)
        if callable(close_fn):
            await cast(Any, close_fn)()
