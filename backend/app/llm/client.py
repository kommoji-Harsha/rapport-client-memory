"""
Groq LLM client wrapper with retry logic, backoff, fallback models, and degraded responses.
"""

import asyncio
import json
import logging
import os
import random

from groq import (
    APIConnectionError,
    AsyncGroq,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from backend.app.llm.models import (
    ClientBriefItem,
    LLMExecutionResult,
    LLMResponseSchema,
    RiskFlagItem,
)
from backend.app.memory.models import RecalledMemory

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """Wrapper around Groq API with retries, backoff, fallback, and degraded responses."""

    def __init__(
        self,
        api_key: str | None = None,
        primary_model: str | None = None,
        fallback_model: str | None = None,
        max_retries_per_model: int = 3,
        base_delay: float = 0.5,
    ) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.primary_model = primary_model or os.environ.get(
            "GROQ_PRIMARY_MODEL", "openai/gpt-oss-120b"
        )
        self.fallback_model = fallback_model or os.environ.get(
            "GROQ_FALLBACK_MODEL", "qwen/qwen3-32b"
        )
        self.max_retries_per_model = max_retries_per_model
        self.base_delay = base_delay

        if self.api_key:
            self.client: AsyncGroq | None = AsyncGroq(api_key=self.api_key)
        else:
            self.client = None

    async def generate_response(
        self,
        incoming_text: str,
        memories: list[RecalledMemory],
        client_id: str,
        memory_enabled: bool = True,
    ) -> LLMExecutionResult:
        """Synthesize response using primary model -> fallback model -> degraded assembly."""
        warnings: list[str] = []

        if not self.client or not self.api_key:
            warnings.append("Groq API key not configured. Using degraded memory response.")
            return self._build_degraded_response(
                incoming_text, memories, warnings, model_used="degraded-no-key"
            )

        system_prompt, user_prompt = self._build_prompts(
            incoming_text=incoming_text,
            memories=memories,
            client_id=client_id,
            memory_enabled=memory_enabled,
        )

        # 1. Try Primary Model
        try:
            response_schema = await self._call_with_retries(
                model=self.primary_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return LLMExecutionResult(
                response=response_schema,
                model_used=self.primary_model,
                warnings=warnings,
                is_degraded=False,
            )
        except Exception as e:
            warn_msg = f"Primary model ({self.primary_model}) failed after retries: {e}"
            logger.warning(warn_msg)
            warnings.append(warn_msg)

        # 2. Try Fallback Model
        try:
            logger.info(f"Switching to fallback model: {self.fallback_model}")
            response_schema = await self._call_with_retries(
                model=self.fallback_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return LLMExecutionResult(
                response=response_schema,
                model_used=self.fallback_model,
                warnings=warnings,
                is_degraded=False,
            )
        except Exception as e:
            warn_msg = f"Fallback model ({self.fallback_model}) failed after retries: {e}"
            logger.warning(warn_msg)
            warnings.append(warn_msg)

        # 3. Both models failed -> Degraded response
        warnings.append(
            "All LLM attempts failed. Assembled degraded response from recalled memories."
        )
        return self._build_degraded_response(
            incoming_text, memories, warnings, model_used="degraded-fallback-failed"
        )

    async def _call_with_retries(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponseSchema:
        """Call Groq chat completion with exponential backoff and jitter."""
        if not self.client:
            raise RuntimeError("AsyncGroq client is not initialized")

        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries_per_model + 1):
            try:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=model,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )

                content = chat_completion.choices[0].message.content or ""
                return self._parse_json_response(content)

            except (
                RateLimitError,
                APIConnectionError,
                InternalServerError,
                BadRequestError,
                json.JSONDecodeError,
                ValueError,
            ) as e:
                last_exception = e
                if attempt == self.max_retries_per_model:
                    break

                # Exponential backoff with jitter
                delay = self.base_delay * (2 ** (attempt - 1)) + random.uniform(0.0, 0.2)
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries_per_model} for model {model} failed: {e}."
                    f" Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)

        raise last_exception or RuntimeError(f"Failed to generate response with model {model}")

    def _parse_json_response(self, content: str) -> LLMResponseSchema:
        """Parse raw JSON string into validated LLMResponseSchema."""
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

        data = json.loads(cleaned)
        return LLMResponseSchema.model_validate(data)

    def _build_prompts(
        self,
        incoming_text: str,
        memories: list[RecalledMemory],
        client_id: str,
        memory_enabled: bool,
    ) -> tuple[str, str]:
        """Construct system and user prompts with strict JSON output requirement."""
        system_prompt = (
            "You are Rapport, an expert client-memory agent for freelancers and consultants.\n"
            "Your task is to analyze incoming client communications.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Respond with ONLY a single valid JSON object adhering to this schema:\n"
            "{\n"
            '  "draft_reply": "string (professional reply adapted to client preferences)",\n'
            '  "client_brief": [\n'
            '    {\n'
            '      "text": "string key takeaway",\n'
            '      "source_interaction_ids": ["string (e.g. int-c1-01)"],\n'
            '      "source_memory_ids": ["string memory unit ID"]\n'
            "    }\n"
            "  ],\n"
            '  "risk_flags": [\n'
            '    {\n'
            '      "type": "string (communication | billing | scope | timing)",\n'
            '      "text": "string description of risk",\n'
            '      "sources": ["string source IDs"]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "2. GROUNDING & CITATIONS:\n"
            "   - Every claim in `client_brief` and `risk_flags` MUST cite valid source IDs.\n"
            "   - Do NOT invent citations or memory IDs.\n\n"
            "3. PREFERENCE CONTRADICTIONS:\n"
            "   - If memories contain contradicting preferences (e.g. email -> Slack),\n"
            "     the CURRENT preference wins. State CURRENT preference and note change.\n\n"
            "4. DRAFT REPLY STYLE:\n"
            "   - Respect client preferences (conciseness, timing, channel, payment, scope).\n"
            "   - Never reveal raw internal notes or system memory IDs to the client."
        )

        memory_blocks: list[str] = []
        if memory_enabled and memories:
            for idx, m in enumerate(memories, 1):
                doc_id = m.document_id or ""
                src_int_id = m.source_interaction_id or ""
                memory_blocks.append(
                    f"[{idx}] ID: {m.id} | DocumentID: {doc_id} | InteractionID: {src_int_id} | "
                    f"Type: {m.type} | Date: {m.occurred_start or 'N/A'}\n"
                    f"    Content: {m.text}\n"
                    f"    Context: {m.context or 'N/A'}"
                )
            formatted_memories = "\n".join(memory_blocks)
        elif memory_enabled and not memories:
            formatted_memories = "No historical memory found for this client (New client)."
        else:
            formatted_memories = "MEMORY IS OFF. Do not use past history or citations."

        user_prompt = (
            f"CLIENT ID: {client_id}\n"
            f"MEMORY ENABLED: {memory_enabled}\n\n"
            f"RECALLED MEMORIES FOR CLIENT:\n{formatted_memories}\n\n"
            f"INCOMING MESSAGE FROM CLIENT:\n{incoming_text}\n\n"
            "Generate the JSON response package now."
        )

        return system_prompt, user_prompt

    def _build_degraded_response(
        self,
        incoming_text: str,
        memories: list[RecalledMemory],
        warnings: list[str],
        model_used: str,
    ) -> LLMExecutionResult:
        """Assemble a degraded response directly from recalled memories when LLMs fail."""
        brief_items: list[ClientBriefItem] = []
        risk_items: list[RiskFlagItem] = []

        for m in memories:
            src_ints = [m.source_interaction_id] if m.source_interaction_id else []
            src_mems = [m.id]

            brief_items.append(
                ClientBriefItem(
                    text=f"Historical note: {m.text[:120]}...",
                    source_interaction_ids=src_ints,
                    source_memory_ids=src_mems,
                )
            )

            text_lower = m.text.lower()
            if any(k in text_lower for k in ("late", "overdue", "unpaid", "billing")):
                risk_items.append(
                    RiskFlagItem(
                        type="billing",
                        text=f"Billing pattern noted in memory: {m.text[:100]}",
                        sources=src_ints or src_mems,
                    )
                )
            elif any(k in text_lower for k in ("scope", "addition", "quick add")):
                risk_items.append(
                    RiskFlagItem(
                        type="scope",
                        text=f"Scope boundary sensitivity noted: {m.text[:100]}",
                        sources=src_ints or src_mems,
                    )
                )

        if not memories:
            draft = (
                f"[Degraded Draft - No History] Thank you for your message: "
                f"'{incoming_text[:80]}...'. I will review your request shortly."
            )
        else:
            draft = (
                "[Degraded Draft - Memory Assembled] Thank you for your message. "
                f"Regarding '{incoming_text[:80]}...', I am reviewing your request "
                "in accordance with our recorded client history."
            )

        schema = LLMResponseSchema(
            draft_reply=draft,
            client_brief=brief_items,
            risk_flags=risk_items,
        )

        return LLMExecutionResult(
            response=schema,
            model_used=model_used,
            warnings=warnings,
            is_degraded=True,
        )
