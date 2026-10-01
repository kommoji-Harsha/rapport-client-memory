"""Agent logic orchestrating memory recall, system prompting, LLM synthesis, and citation grounding."""

import asyncio
import logging
import uuid

from backend.app.llm.client import GroqLLMClient
from backend.app.llm.models import AgentResponse, BriefItem, RiskFlag
from backend.app.memory.models import RecalledMemory
from backend.app.memory.protocol import MemoryBackend

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Rapport, an expert client-memory agent for freelancers and consultants.
Your job is to craft a professional draft reply to an incoming client message, summarize key client details in a client brief, and identify risk flags based ONLY on recalled client memory.

CRITICAL INSTRUCTIONS:
1. CITATION GROUNDING:
   - Every brief item and risk flag MUST cite exact source interaction IDs (e.g. 'int_001') or memory IDs provided in the context.
   - NEVER invent or guess citation IDs or facts.
2. PREFERENCE EVOLUTION & CONTRADICTIONS:
   - If memories reveal changing preferences or direct contradictions (e.g. communication channel changed from email to Slack, or call times updated), ALWAYS prioritize the MOST RECENT preference as current.
   - Explicitly note the historical change in the brief or draft.
3. DRAFT STYLING & TONE:
   - Reflect client preferences (e.g., short concise emails, async Slack updates, no early morning calls).
   - Do NOT expose internal memory IDs or raw notes in the draft reply itself.
4. JSON OUTPUT FORMAT:
   Return JSON strictly matching this schema:
   {
     "draft_reply": "Professional message text to send to client...",
     "client_brief": [
       {
         "text": "Brief observation or history note...",
         "source_interaction_ids": ["int_001"],
         "source_memory_ids": ["mem-123"]
       }
     ],
     "risk_flags": [
       {
         "type": "payment|scope|timing|communication",
         "text": "Risk description...",
         "sources": ["int_001"]
       }
     ]
   }
"""


class RapportAgentService:
    """Agent service handling memory recall, LLM synthesis, and grounding filtering."""

    def __init__(
        self,
        memory_backend: MemoryBackend,
        llm_client: GroqLLMClient | None = None,
    ) -> None:
        self.memory = memory_backend
        self.llm = llm_client or GroqLLMClient()

    async def generate_response(
        self,
        client_id: str,
        client_name: str,
        incoming_text: str,
        memory_enabled: bool = True,
    ) -> AgentResponse:
        response_id = f"resp_{uuid.uuid4().hex[:10]}"
        warnings: list[str] = []
        recalled_memories: list[RecalledMemory] = []

        if memory_enabled:
            try:
                recalled_memories = await self.memory.recall_client(
                    client_id=client_id,
                    query=incoming_text,
                    budget="mid",
                )
            except Exception as mem_err:
                logger.error("Hindsight memory recall failed: %s", mem_err)
                warnings.append(f"Memory recall error: {mem_err}. Proceeding with degraded response.")
                recalled_memories = []

        # Check if new client with no history
        if memory_enabled and not recalled_memories and not warnings:
            warnings.append("No past memory found for this client (new client or initial interaction).")

        # Build user prompt
        user_prompt = self._build_user_prompt(client_id, client_name, incoming_text, memory_enabled, recalled_memories)

        # Call LLM client
        structured_output, model_used, llm_warnings = await self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            recalled_memories=recalled_memories,
        )
        warnings.extend(llm_warnings)

        # Apply strict citation grounding
        grounded_brief, grounded_risks = self._ground_citations(
            raw_brief=structured_output.client_brief,
            raw_risks=structured_output.risk_flags,
            recalled_memories=recalled_memories,
            is_new_client=(memory_enabled and not recalled_memories),
        )

        return AgentResponse(
            response_id=response_id,
            client_id=client_id,
            incoming_text=incoming_text,
            memory_enabled=memory_enabled,
            draft_reply=structured_output.draft_reply,
            client_brief=grounded_brief,
            risk_flags=grounded_risks,
            memory_used=recalled_memories if memory_enabled else [],
            warnings=warnings,
            model_used=model_used,
        )

    async def compare_responses(
        self,
        client_id: str,
        client_name: str,
        incoming_text: str,
    ) -> dict[str, AgentResponse]:
        """Run memory_enabled=True and memory_enabled=False in parallel."""
        task_on = self.generate_response(client_id, client_name, incoming_text, memory_enabled=True)
        task_off = self.generate_response(client_id, client_name, incoming_text, memory_enabled=False)

        resp_on, resp_off = await asyncio.gather(task_on, task_off)
        return {"memory_on": resp_on, "memory_off": resp_off}

    def _build_user_prompt(
        self,
        client_id: str,
        client_name: str,
        incoming_text: str,
        memory_enabled: bool,
        recalled_memories: list[RecalledMemory],
    ) -> str:
        prompt_parts = [
            f"CLIENT ID: {client_id}",
            f"CLIENT NAME: {client_name}",
            f"MEMORY ENABLED: {memory_enabled}",
            f"INCOMING MESSAGE:\n\"\"\"{incoming_text}\"\"\"\n",
        ]

        if memory_enabled and recalled_memories:
            prompt_parts.append("RECALLED MEMORY HISTORY:")
            for idx, mem in enumerate(recalled_memories, start=1):
                int_id = mem.source_interaction_id or "N/A"
                occurred = mem.occurred_start or "Unknown"
                prompt_parts.append(
                    f"[{idx}] Memory ID: {mem.id} | Interaction ID: {int_id} | Date: {occurred} | Type: {mem.type}\n"
                    f"    Context: {mem.context}\n"
                    f"    Content: {mem.text}\n"
                )
        elif memory_enabled:
            prompt_parts.append("RECALLED MEMORY HISTORY: [No past history recorded for this client yet]")
        else:
            prompt_parts.append("MEMORY DISABLED: Craft a generic professional draft response without memory context.")

        return "\n".join(prompt_parts)

    def _ground_citations(
        self,
        raw_brief: list[BriefItem],
        raw_risks: list[RiskFlag],
        recalled_memories: list[RecalledMemory],
        is_new_client: bool,
    ) -> tuple[list[BriefItem], list[RiskFlag]]:
        """Drop any citation ID not in recalled memories set."""
        valid_mem_ids = {mem.id for mem in recalled_memories}
        valid_int_ids = {mem.source_interaction_id for mem in recalled_memories if mem.source_interaction_id}

        grounded_brief: list[BriefItem] = []
        for item in raw_brief:
            filtered_ints = [iid for iid in item.source_interaction_ids if iid in valid_int_ids]
            filtered_mems = [mid for mid in item.source_memory_ids if mid in valid_mem_ids]

            grounded_brief.append(
                BriefItem(
                    text=item.text,
                    source_interaction_ids=filtered_ints,
                    source_memory_ids=filtered_mems,
                )
            )

        grounded_risks: list[RiskFlag] = []
        for risk in raw_risks:
            filtered_sources = [s for s in risk.sources if s in valid_int_ids or s in valid_mem_ids]
            grounded_risks.append(
                RiskFlag(
                    type=risk.type,
                    text=risk.text,
                    sources=filtered_sources,
                )
            )

        if is_new_client and not grounded_brief:
            grounded_brief = [
                BriefItem(
                    text="New client: no prior interaction history recorded yet.",
                    source_interaction_ids=[],
                    source_memory_ids=[],
                )
            ]

        return grounded_brief, grounded_risks
