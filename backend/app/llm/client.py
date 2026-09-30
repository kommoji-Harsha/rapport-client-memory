"""Groq LLM client wrapper with retry logic, model fallback, and graceful degradation."""

import asyncio
import json
import logging
import os
import random

import groq
from groq import AsyncGroq

from backend.app.llm.models import BriefItem, LLMStructuredOutput, RiskFlag
from backend.app.memory.models import RecalledMemory

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """LLM client wrapping official Groq AsyncGroq SDK with retry and fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        primary_model: str | None = None,
        fallback_model: str | None = None,
        max_retries_per_model: int = 3,
        request_timeout: float = 30.0,
    ) -> None:
        key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.client = AsyncGroq(api_key=key) if key else None
        self.primary_model = primary_model or os.environ.get("GROQ_PRIMARY_MODEL", "openai/gpt-oss-120b")
        self.fallback_model = fallback_model or os.environ.get("GROQ_FALLBACK_MODEL", "qwen/qwen3-32b")
        self.max_retries_per_model = max_retries_per_model
        self.request_timeout = request_timeout

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        recalled_memories: list[RecalledMemory] | None = None,
    ) -> tuple[LLMStructuredOutput, str, list[str]]:
        """Generate structured response using primary model -> fallback model -> degraded response.

        Returns:
            (LLMStructuredOutput, model_used, warnings)
        """
        warnings: list[str] = []

        if not self.client:
            logger.warning("GROQ_API_KEY not configured. Falling back to degraded response generation.")
            warnings.append("Groq API key not configured; using degraded memory-assembled draft.")
            degraded = self._build_degraded_response(user_prompt, recalled_memories)
            return degraded, "degraded_fallback", warnings

        # Try Primary Model
        try:
            output = await self._call_with_retries(
                model=self.primary_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return output, self.primary_model, warnings
        except Exception as primary_err:
            logger.warning("Primary model %s failed after retries: %s", self.primary_model, primary_err)
            warnings.append(f"Primary model {self.primary_model} failed: {primary_err}. Switched to fallback model.")

        # Try Fallback Model
        try:
            output = await self._call_with_retries(
                model=self.fallback_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return output, self.fallback_model, warnings
        except Exception as fallback_err:
            logger.error("Fallback model %s also failed after retries: %s", self.fallback_model, fallback_err)
            warnings.append(f"Fallback model {self.fallback_model} failed: {fallback_err}. Generated degraded response.")

        # Both failed: assemble degraded response
        degraded = self._build_degraded_response(user_prompt, recalled_memories)
        return degraded, "degraded_fallback", warnings

    async def _call_with_retries(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMStructuredOutput:
        last_error: Exception | None = None

        for attempt in range(self.max_retries_per_model):
            try:
                # Execute API call with timeout
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(  # type: ignore[union-attr]
                        model=model,
                        temperature=0.0,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    ),
                    timeout=self.request_timeout,
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Received empty content from Groq API")

                parsed_json = json.loads(content)
                validated = LLMStructuredOutput.model_validate(parsed_json)
                return validated

            except (TimeoutError, groq.RateLimitError, groq.APIConnectionError, groq.APITimeoutError, groq.BadRequestError, groq.APIStatusError, json.JSONDecodeError, ValueError) as err:
                last_error = err
                logger.info("Attempt %d/%d for model %s failed: %s", attempt + 1, self.max_retries_per_model, model, err)
                if attempt < self.max_retries_per_model - 1:
                    # Exponential backoff with jitter
                    backoff = (2**attempt) * 0.5 + random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)

        raise RuntimeError(f"All {self.max_retries_per_model} attempts failed for model {model}: {last_error}")

    def _build_degraded_response(
        self,
        user_prompt: str,
        recalled_memories: list[RecalledMemory] | None,
    ) -> LLMStructuredOutput:
        """Construct a safe degraded response directly from recalled memories if LLM fails."""
        brief_items: list[BriefItem] = []
        risk_flags: list[RiskFlag] = []

        if recalled_memories:
            for mem in recalled_memories:
                int_id = mem.source_interaction_id
                sources = [int_id] if int_id else []
                mem_sources = [mem.id]

                if "payment" in mem.text.lower() or "late" in mem.text.lower() or "invoice" in mem.text.lower():
                    risk_flags.append(
                        RiskFlag(
                            type="payment",
                            text=f"Note on payment history: {mem.text[:100]}...",
                            sources=sources or mem_sources,
                        )
                    )
                elif "scope" in mem.text.lower() or "request" in mem.text.lower():
                    risk_flags.append(
                        RiskFlag(
                            type="scope",
                            text=f"Note on scope management: {mem.text[:100]}...",
                            sources=sources or mem_sources,
                        )
                    )

                brief_items.append(
                    BriefItem(
                        text=mem.text,
                        source_interaction_ids=sources,
                        source_memory_ids=mem_sources,
                    )
                )

        draft = (
            "Thank you for your message. I have received your request and am reviewing the details. "
            "I will get back to you shortly with next steps."
        )

        return LLMStructuredOutput(
            draft_reply=draft,
            client_brief=brief_items[:5],
            risk_flags=risk_flags[:3],
        )
