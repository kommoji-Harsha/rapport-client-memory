"""HindsightMemory implementation using official hindsight-client."""

import logging
import os
from datetime import UTC, datetime
from typing import Any

from hindsight_client import Hindsight

from backend.app.memory.models import ObservationItem, RecalledMemory

logger = logging.getLogger(__name__)


class HindsightMemory:
    """Production memory backend backed by Hindsight Cloud."""

    def __init__(
        self,
        bank_id: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.bank_id = bank_id or os.environ.get("HINDSIGHT_BANK_ID", "rapport-client-memory-bank")
        url = base_url or os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
        key = api_key or os.environ.get("HINDSIGHT_API_KEY", "")
        if not key:
            raise ValueError("HINDSIGHT_API_KEY environment variable is required for HindsightMemory.")

        self.client = Hindsight(
            base_url=url,
            api_key=key,
            timeout=timeout,
        )

    async def bootstrap_bank(self) -> None:
        """Create bank with client-relationship mission and observations enabled if not already present."""
        try:
            await self.client.acreate_bank(
                bank_id=self.bank_id,
                name="Rapport Client Memory",
                mission="Client relationship management, communication preferences, payment history, and scope tracking for freelancers and consultants.",
                enable_observations=True,
            )
            logger.info("Created Hindsight memory bank with observations enabled: %s", self.bank_id)
        except Exception as err:
            logger.info("Bank bootstrap notice for %s: %s", self.bank_id, err)

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

        meta: dict[str, str] = {}
        if metadata:
            meta = {str(k): str(v) for k, v in metadata.items()}
        meta["client_id"] = str(client_id)
        meta["interaction_id"] = str(interaction_id)

        dt: datetime | None = None
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
            except ValueError:
                dt = None

        doc_id = f"interaction:{interaction_id}"

        await self.client.aretain(
            bank_id=self.bank_id,
            content=content,
            context=context,
            timestamp=dt,
            document_id=doc_id,
            metadata=meta,
            tags=all_tags,
            retain_async=False,
        )

    async def retain_batch_interactions(
        self,
        items: list[dict[str, Any]],
    ) -> None:
        batch_items: list[dict[str, Any]] = []
        for raw_item in items:
            client_id = raw_item.get("client_id")
            raw_meta = raw_item.get("metadata", {})
            if not client_id and "client_id" in raw_meta:
                client_id = raw_meta["client_id"]

            tags = list(raw_item.get("tags", []))
            if client_id:
                client_tag = f"client:{client_id}"
                if client_tag not in tags:
                    tags.append(client_tag)

            doc_id = raw_item.get("document_id") or raw_item.get("id")
            meta = {str(k): str(v) for k, v in raw_meta.items()}
            if client_id:
                meta["client_id"] = str(client_id)

            item_dict: dict[str, Any] = {
                "content": raw_item.get("content") or raw_item.get("text", ""),
                "context": raw_item.get("context", ""),
                "metadata": meta,
                "tags": tags,
            }
            if doc_id:
                item_dict["document_id"] = str(doc_id)

            ts_str = raw_item.get("timestamp") or raw_item.get("occurred_start")
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    item_dict["timestamp"] = dt
                except ValueError:
                    pass

            batch_items.append(item_dict)

        await self.client.aretain_batch(
            bank_id=self.bank_id,
            items=batch_items,
            retain_async=False,
        )

    async def retain_feedback(
        self,
        client_id: str,
        response_id: str,
        outcome: str,
        notes: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        client_tag = f"client:{client_id}"
        tags = [client_tag, "type:feedback", f"outcome:{outcome}"]
        doc_id = f"feedback:{response_id}"
        content = f"Feedback on response {response_id}: outcome={outcome}."
        if notes:
            content += f" Notes: {notes}"

        dt: datetime | None = None
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
            except ValueError:
                dt = None

        meta = {
            "client_id": str(client_id),
            "response_id": str(response_id),
            "outcome": str(outcome),
            "notes": str(notes or ""),
        }

        await self.client.aretain(
            bank_id=self.bank_id,
            content=content,
            context="User draft response feedback outcome",
            timestamp=dt,
            document_id=doc_id,
            metadata=meta,
            tags=tags,
            retain_async=False,
        )

    async def recall_client(
        self,
        client_id: str,
        query: str,
        budget: str = "mid",
    ) -> list[RecalledMemory]:
        client_tag = f"client:{client_id}"
        resp = await self.client.arecall(
            bank_id=self.bank_id,
            query=query,
            budget=budget,
            tags=[client_tag],
            tags_match="any_strict",
            include_chunks=True,
            include_source_facts=True,
        )

        results: list[RecalledMemory] = []
        raw_results = getattr(resp, "results", []) or []

        for item in raw_results:
            doc_id = getattr(item, "document_id", None)
            meta = getattr(item, "metadata", {}) or {}
            source_int_id = meta.get("interaction_id")
            if not source_int_id and doc_id and isinstance(doc_id, str) and doc_id.startswith("interaction:"):
                source_int_id = doc_id.replace("interaction:", "")

            scores_raw = getattr(item, "scores", None)
            scores_dict: dict[str, float | None] = {}
            if scores_raw is not None:
                if isinstance(scores_raw, dict):
                    for k in ["final", "reranker", "semantic", "keyword"]:
                        if k in scores_raw:
                            val = scores_raw[k]
                            scores_dict[k] = float(val) if val is not None else None
                else:
                    for attr in ["final", "reranker", "semantic", "keyword"]:
                        val = getattr(scores_raw, attr, None)
                        scores_dict[attr] = float(val) if val is not None else None

            results.append(
                RecalledMemory(
                    id=getattr(item, "id", ""),
                    text=getattr(item, "text", ""),
                    type=getattr(item, "type", "experience"),
                    context=getattr(item, "context", None),
                    metadata=meta if isinstance(meta, dict) else {},
                    tags=list(getattr(item, "tags", []) or []),
                    entities=list(getattr(item, "entities", []) or []),
                    occurred_start=str(getattr(item, "occurred_start", "")) or None,
                    mentioned_at=str(getattr(item, "mentioned_at", "")) or None,
                    document_id=doc_id,
                    chunk_id=getattr(item, "chunk_id", None),
                    source_fact_ids=list(getattr(item, "source_fact_ids", []) or []),
                    scores=scores_dict,
                    source_interaction_id=source_int_id,
                )
            )

        return results

    async def list_observations(
        self,
        client_id: str,
    ) -> list[ObservationItem]:
        client_tag = f"client:{client_id}"
        obs_items: list[ObservationItem] = []

        try:
            resp = await self.client.arecall(
                bank_id=self.bank_id,
                query="client observations preferences behavior",
                types=["observation"],
                tags=[client_tag],
                tags_match="any_strict",
                prefer_observations=True,
            )
            raw_results = getattr(resp, "results", []) or []
            for item in raw_results:
                obs_items.append(
                    ObservationItem(
                        id=getattr(item, "id", ""),
                        text=getattr(item, "text", ""),
                        context=getattr(item, "context", None),
                        client_id=client_id,
                        metadata=getattr(item, "metadata", {}) or {},
                    )
                )
            return obs_items
        except Exception as err:
            logger.info("arecall observations notice for %s: %s", client_id, err)

        if hasattr(self.client, "alist_memories"):
            try:
                list_resp = await self.client.alist_memories(
                    bank_id=self.bank_id,
                    type="observation",
                )
                items = getattr(list_resp, "items", getattr(list_resp, "results", [])) or []
                for item in items:
                    tags = getattr(item, "tags", []) or []
                    if client_tag in tags:
                        obs_items.append(
                            ObservationItem(
                                id=getattr(item, "id", ""),
                                text=getattr(item, "text", ""),
                                context=getattr(item, "context", None),
                                client_id=client_id,
                                metadata=getattr(item, "metadata", {}) or {},
                            )
                        )
            except Exception as err:
                logger.info("alist_memories notice for %s: %s", client_id, err)

        return obs_items

    async def close(self) -> None:
        if hasattr(self.client, "aclose"):
            await self.client.aclose()  # type: ignore[no-untyped-call]
