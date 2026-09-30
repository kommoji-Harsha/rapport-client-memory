#!/usr/bin/env python3
"""Seed script for populating Hindsight Memory and local DB with client synthetic data.

Usage:
    python scripts/seed.py [--use-fake]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add root directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.memory.fake import FakeMemory
from backend.app.memory.hindsight_memory import HindsightMemory
from backend.app.memory.protocol import MemoryBackend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")


async def seed(memory_backend: MemoryBackend, clients_path: Path, interactions_path: Path) -> None:
    logger.info("Starting seed process...")

    # Load data files
    with open(clients_path, encoding="utf-8") as f:
        clients = json.load(f)

    with open(interactions_path, encoding="utf-8") as f:
        interactions = json.load(f)

    logger.info("Loaded %d clients and %d interactions from JSON", len(clients), len(interactions))

    # 1. Bootstrap bank
    logger.info("Bootstrapping memory bank...")
    await memory_backend.bootstrap_bank()

    # 2. Prepare items for batch retention
    batch_items = []
    for int_data in interactions:
        client_id = int_data["client_id"]
        doc_id = f"interaction:{int_data['id']}"

        item = {
            "content": int_data["content"],
            "context": int_data.get("context", f"Interaction with client {client_id}"),
            "timestamp": int_data["timestamp"],
            "document_id": doc_id,
            "metadata": {
                "client_id": client_id,
                "interaction_id": int_data["id"],
                "type": int_data.get("type", "email"),
            },
            "tags": [f"client:{client_id}", f"type:{int_data.get('type', 'email')}"],
        }
        batch_items.append(item)

    # 3. Retain batch with progress reporting
    batch_size = 10
    total_items = len(batch_items)
    logger.info("Retaining %d interactions in batches of %d...", total_items, batch_size)

    for i in range(0, total_items, batch_size):
        chunk = batch_items[i : i + batch_size]
        await memory_backend.retain_batch_interactions(chunk)
        processed = min(i + batch_size, total_items)
        logger.info("Progress: %d/%d interactions retained (%.1f%%)", processed, total_items, (processed / total_items) * 100)

    logger.info("Seed complete! Successfully retained %d interactions across %d clients.", total_items, len(clients))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic clients and interactions into Hindsight Memory.")
    parser.add_argument("--use-fake", action="store_true", help="Use FakeMemory instead of real Hindsight Cloud")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    clients_path = root_dir / "data" / "clients.json"
    interactions_path = root_dir / "data" / "interactions.json"

    if args.use_fake:
        logger.info("Using FakeMemory backend for seeding dry-run")
        backend: MemoryBackend = FakeMemory()
    else:
        api_key = os.environ.get("HINDSIGHT_API_KEY")
        if not api_key:
            logger.error("HINDSIGHT_API_KEY environment variable is missing! Pass --use-fake for offline dry run.")
            sys.exit(1)
        backend = HindsightMemory()

    try:
        await seed(backend, clients_path, interactions_path)
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
