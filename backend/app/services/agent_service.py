"""
Agent service orchestrating recall -> LLM synthesis -> grounding validation.
"""

import asyncio
import logging

from backend.app.core.grounding import validate_and_filter_grounding
from backend.app.core.models import AgentResponsePackage, CompareAgentResponsePackage
from backend.app.llm.client import GroqLLMClient
from backend.app.memory.models import RecalledMemory
from backend.app.memory.protocol import MemoryBackend

logger = logging.getLogger(__name__)


class RapportAgentService:
    """Orchestrates memory recall, LLM synthesis, and grounding verification."""

    def __init__(
        self,
        memory_backend: MemoryBackend,
        llm_client: GroqLLMClient,
    ) -> None:
        self.memory = memory_backend
        self.llm = llm_client

    async def process_incoming_message(
        self,
        client_id: str,
        incoming_text: str,
        memory_enabled: bool = True,
    ) -> AgentResponsePackage:
        """Process incoming message for a client with or without long-term memory."""
        recalled_memories: list[RecalledMemory] = []
        warnings: list[str] = []

        if memory_enabled:
            try:
                recalled_memories = await self.memory.recall_client(
                    client_id=client_id,
                    query=incoming_text,
                    budget="mid",
                )
            except Exception as e:
                warn_msg = f"Hindsight memory recall failed: {e}. Degrading to memory-off mode."
                logger.warning(warn_msg)
                warnings.append(warn_msg)
                recalled_memories = []

        # Synthesize via LLM
        exec_result = await self.llm.generate_response(
            incoming_text=incoming_text,
            memories=recalled_memories,
            client_id=client_id,
            memory_enabled=memory_enabled and len(recalled_memories) > 0,
        )

        all_warnings = warnings + exec_result.warnings

        # Validate grounding citations
        if memory_enabled and recalled_memories:
            grounded_schema = validate_and_filter_grounding(
                exec_result.response, recalled_memories
            )
        else:
            # Memory OFF or no memories -> ensure zero citations
            grounded_schema = exec_result.response
            grounded_schema.client_brief = [
                b.model_copy(update={"source_interaction_ids": [], "source_memory_ids": []})
                for b in grounded_schema.client_brief
            ]
            grounded_schema.risk_flags = [
                r.model_copy(update={"sources": []}) for r in grounded_schema.risk_flags
            ]

        return AgentResponsePackage(
            draft_reply=grounded_schema.draft_reply,
            client_brief=grounded_schema.client_brief,
            risk_flags=grounded_schema.risk_flags,
            memory_used=recalled_memories if memory_enabled else [],
            warnings=all_warnings,
            model_used=exec_result.model_used,
            is_degraded=exec_result.is_degraded,
        )

    async def compare_response(
        self,
        client_id: str,
        incoming_text: str,
    ) -> CompareAgentResponsePackage:
        """Run memory-ON and memory-OFF pipelines in parallel for comparison."""
        res_on, res_off = await asyncio.gather(
            self.process_incoming_message(client_id, incoming_text, memory_enabled=True),
            self.process_incoming_message(client_id, incoming_text, memory_enabled=False),
        )
        return CompareAgentResponsePackage(
            memory_on=res_on,
            memory_off=res_off,
        )
