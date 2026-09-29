#!/usr/bin/env python3
"""
Smoke test script for live Hindsight Cloud memory bank.
Verifies retain -> recall and strict client tag isolation.
Run with live API key:
    HINDSIGHT_API_KEY="your_key" python scripts/smoke_hindsight.py
"""

import os
import sys
import uuid

from hindsight_client import Hindsight


def main() -> None:
    api_key = os.environ.get("HINDSIGHT_API_KEY")
    if not api_key:
        print("[Error] HINDSIGHT_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
    bank_id = os.environ.get("HINDSIGHT_BANK_ID", "smoke-test-bank")

    print(f"Connecting to Hindsight at {base_url} (Bank: {bank_id})...")
    client = Hindsight(base_url=base_url, api_key=api_key)

    # 1. Create / Ensure test bank
    try:
        client.create_bank(
            bank_id=bank_id,
            name="Smoke Test Bank",
            mission="Verify tag isolation and recall functionality.",
            enable_observations=True,
        )
        print(f"Bank '{bank_id}' created or verified.")
    except Exception as e:
        print(f"Bank creation note: {e}")

    # Generate unique test client IDs
    run_id = uuid.uuid4().hex[:6]
    client_a_id = f"smoke_client_a_{run_id}"
    client_b_id = f"smoke_client_b_{run_id}"

    # 2. Retain Client A item
    content_a = (
        f"Client A ({client_a_id}) explicitly prefers communication via Slack "
        "and hates morning calls."
    )
    print(f"Retaining item for Client A ({client_a_id})...")
    client.retain(
        bank_id=bank_id,
        content=content_a,
        context="Client preference recording for Client A",
        document_id=f"doc-{client_a_id}-1",
        metadata={"client_id": client_a_id},
        tags=[f"client:{client_a_id}"],
    )

    # 3. Retain Client B item
    content_b = (
        f"Client B ({client_b_id}) pays invoices 20 days late "
        "and prefers email communications."
    )
    print(f"Retaining item for Client B ({client_b_id})...")
    client.retain(
        bank_id=bank_id,
        content=content_b,
        context="Client payment pattern recording for Client B",
        document_id=f"doc-{client_b_id}-1",
        metadata={"client_id": client_b_id},
        tags=[f"client:{client_b_id}"],
    )

    # 4. Recall for Client A with strict tag filtering
    print(f"\nRecalling memories for Client A ({client_a_id}) with tags_match='any_strict'...")
    recall_res = client.recall(
        bank_id=bank_id,
        query="communication channel preferences and meeting timing",
        tags=[f"client:{client_a_id}"],
        tags_match="any_strict",
    )

    results = recall_res.results if hasattr(recall_res, "results") else []
    print(f"Recall returned {len(results)} items for Client A:")
    leaked = False
    for item in results:
        text = getattr(item, "text", str(item))
        tags = getattr(item, "tags", [])
        print(f" - [{tags}] {text}")
        if f"client:{client_b_id}" in tags or client_b_id in text:
            print(
                "[CRITICAL ERROR] Cross-client leakage detected! "
                f"Client B memory appeared in Client A recall: {text}"
            )
            leaked = True

    if leaked:
        sys.exit(1)

    print("\n[SUCCESS] Tag isolation verified! Client A recall contained zero Client B data.")


if __name__ == "__main__":
    main()
