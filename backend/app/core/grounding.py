"""
Grounding validation logic.
Ensures every citation ID referenced in LLM brief items or risk flags exists
in the set of recalled memory IDs or source interaction IDs.
"""

from backend.app.llm.models import ClientBriefItem, LLMResponseSchema, RiskFlagItem
from backend.app.memory.models import RecalledMemory


def validate_and_filter_grounding(
    llm_schema: LLMResponseSchema,
    recalled_memories: list[RecalledMemory],
) -> LLMResponseSchema:
    """Validate citations against recalled memories and drop hallucinated citation IDs."""
    valid_memory_ids = {m.id for m in recalled_memories}
    valid_interaction_ids = {
        m.source_interaction_id for m in recalled_memories if m.source_interaction_id
    }
    valid_doc_ids = {m.document_id for m in recalled_memories if m.document_id}

    all_valid_ids = valid_memory_ids | valid_interaction_ids | valid_doc_ids

    # 1. Filter Client Brief Items
    filtered_brief: list[ClientBriefItem] = []
    for brief_item in llm_schema.client_brief:
        valid_src_ints = [
            sid for sid in brief_item.source_interaction_ids if sid in all_valid_ids
        ]
        valid_src_mems = [
            mid for mid in brief_item.source_memory_ids if mid in all_valid_ids
        ]

        filtered_brief.append(
            ClientBriefItem(
                text=brief_item.text,
                source_interaction_ids=valid_src_ints,
                source_memory_ids=valid_src_mems,
            )
        )

    # 2. Filter Risk Flags
    filtered_risks: list[RiskFlagItem] = []
    for risk_item in llm_schema.risk_flags:
        valid_sources = [s for s in risk_item.sources if s in all_valid_ids]
        filtered_risks.append(
            RiskFlagItem(
                type=risk_item.type,
                text=risk_item.text,
                sources=valid_sources,
            )
        )

    return LLMResponseSchema(
        draft_reply=llm_schema.draft_reply,
        client_brief=filtered_brief,
        risk_flags=filtered_risks,
    )
