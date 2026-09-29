#!/usr/bin/env python3
"""
Seed script to retain client interaction history into Hindsight memory bank.
Idempotent and provides progress output.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from hindsight_client import Hindsight


def load_json(filepath: Path) -> list[dict[str, Any]]:
    with open(filepath, "r", encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)
        return data


def main() -> None:
    api_key = os.environ.get("HINDSIGHT_API_KEY")
    if not api_key:
        print("[Error] HINDSIGHT_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
    bank_id = os.environ.get("HINDSIGHT_BANK_ID", "rapport-freelancer-memory")

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data"

    clients_file = data_dir / "clients.json"
    interactions_file = data_dir / "interactions.json"

    if not clients_file.exists() or not interactions_file.exists():
        print(f"[Error] Data files missing in {data_dir}", file=sys.stderr)
        sys.exit(1)

    clients = load_json(clients_file)
    interactions = load_json(interactions_file)

    print(f"Connecting to Hindsight at {base_url} (Bank ID: {bank_id})...")
    client = Hindsight(base_url=base_url, api_key=api_key)

    # 1. Bootstrap Bank
    try:
        print(f"Ensuring memory bank '{bank_id}' exists...")
        client.create_bank(
            bank_id=bank_id,
            name="Rapport Freelancer Client Memory",
            mission=(
                "Maintain accurate, isolated client interaction histories, "
                "communication preferences, billing patterns, decision-maker hierarchies, "
                "and scope boundaries for freelancer consulting engagements."
            ),
            enable_observations=True,
        )
        print("Memory bank verified/created successfully.")
    except Exception as e:
        print(f"[Note] create_bank status: {e}")

    # 2. Prepare items for retain_batch
    items_to_retain: list[dict[str, Any]] = []

    # First, retain client profiles
    for c in clients:
        doc_id = f"client-profile-{c['id']}"
        items_to_retain.append({
            "content": (
                f"Client Profile: {c['name']} ({c['industry']}). "
                f"Primary Contact: {c['primary_contact']}. Key Quirks: {c['quirks']}"
            ),
            "context": f"Client metadata profile for {c['name']} (ID: {c['id']}).",
            "document_id": doc_id,
            "metadata": {
                "client_id": c["id"],
                "type": "client_profile",
                "client_name": c["name"],
            },
            "tags": [f"client:{c['id']}", "type:profile"],
            "timestamp": c.get("created_at", "2024-06-01T00:00:00Z"),
        })

    # Second, retain interactions
    for item in interactions:
        client_id = item["client_id"]
        doc_id = f"interaction-{item['id']}"
        metadata = dict(item.get("metadata", {}))
        metadata["client_id"] = client_id
        metadata["interaction_id"] = item["id"]
        metadata["channel"] = item["channel"]

        content_text = f"[{item['channel'].upper()}] {item['summary']}: {item['content']}"
        items_to_retain.append({
            "content": content_text,
            "context": item.get("context", f"Interaction with client {client_id}"),
            "document_id": doc_id,
            "metadata": metadata,
            "tags": [f"client:{client_id}", f"channel:{item['channel']}"],
            "timestamp": item["timestamp"],
        })

    print(f"Retaining {len(items_to_retain)} items into Hindsight bank '{bank_id}'...")

    # Batch retain in chunks if necessary
    batch_size = 20
    for i in range(0, len(items_to_retain), batch_size):
        chunk = items_to_retain[i : i + batch_size]
        try:
            res = client.retain_batch(
                bank_id=bank_id,
                items=chunk,
            )
            total = len(items_to_retain)
            end = min(i + batch_size, total)
            print(f" Retained items {i+1} to {end}/{total}: {res}")
        except Exception as e:
            print(f"[Error] Failed batch retain {i+1}..{i+len(chunk)}: {e}", file=sys.stderr)

    print("Seeding complete!")


if __name__ == "__main__":
    main()
