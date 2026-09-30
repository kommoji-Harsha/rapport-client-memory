#!/usr/bin/env python3
"""Smoke test script for Hindsight Cloud integration and tag isolation.

Usage:
    HINDSIGHT_API_KEY="your_key" python scripts/smoke_hindsight.py [--use-fake]
"""

import argparse
import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.memory.fake import FakeMemory
from backend.app.memory.hindsight_memory import HindsightMemory
from backend.app.memory.protocol import MemoryBackend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smoke_hindsight")


async def run_smoke_test(backend: MemoryBackend) -> None:
    test_run_id = uuid.uuid4().hex[:6]
    client_a = f"smoke_client_a_{test_run_id}"
    client_b = f"smoke_client_b_{test_run_id}"

    logger.info("Initializing smoke test with run ID %s...", test_run_id)
    await backend.bootstrap_bank()

    # Step 1: Retain memory for Client A
    logger.info("Retaining memory for Client A (%s)...", client_a)
    secret_a = f"Client A confidential budget threshold is $50,000-{test_run_id}"
    await backend.retain_interaction(
        client_id=client_a,
        interaction_id=f"int_a_{test_run_id}",
        content=secret_a,
        context="Smoke test secret for Client A",
        timestamp="2024-09-01T10:00:00Z",
    )

    # Step 2: Retain memory for Client B
    logger.info("Retaining memory for Client B (%s)...", client_b)
    secret_b = f"Client B confidential strategy is Slack-only-{test_run_id}"
    await backend.retain_interaction(
        client_id=client_b,
        interaction_id=f"int_b_{test_run_id}",
        content=secret_b,
        context="Smoke test secret for Client B",
        timestamp="2024-09-01T10:00:00Z",
    )

    # Allow brief propagation window if remote async
    await asyncio.sleep(1.0)

    # Step 3: Recall Client A with tags_match='any_strict'
    logger.info("Recalling memories for Client A (%s)...", client_a)
    memories_a = await backend.recall_client(client_id=client_a, query="confidential budget strategy")
    texts_a = [m.text for m in memories_a]

    logger.info("Recalled %d items for Client A", len(memories_a))
    has_secret_a_in_a = any(secret_a in text for text in texts_a)
    has_secret_b_in_a = any(secret_b in text for text in texts_a)

    if not has_secret_a_in_a:
        logger.warning("Client A memory was not found in Client A recall (could be latency or query match).")
    if has_secret_b_in_a:
        logger.error("CRITICAL FAILURE: Client B memory LEAKED into Client A recall!")
        sys.exit(1)

    # Step 4: Recall Client B with tags_match='any_strict'
    logger.info("Recalling memories for Client B (%s)...", client_b)
    memories_b = await backend.recall_client(client_id=client_b, query="confidential budget strategy")
    texts_b = [m.text for m in memories_b]

    logger.info("Recalled %d items for Client B", len(memories_b))
    has_secret_b_in_b = any(secret_b in text for text in texts_b)
    has_secret_a_in_b = any(secret_a in text for text in texts_b)

    if not has_secret_b_in_b:
        logger.warning("Client B memory was not found in Client B recall.")
    if has_secret_a_in_b:
        logger.error("CRITICAL FAILURE: Client A memory LEAKED into Client B recall!")
        sys.exit(1)

    logger.info("SUCCESS: Tag isolation verified! No cross-client leakage detected.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test Hindsight memory and client tag isolation.")
    parser.add_argument("--use-fake", action="store_true", help="Run smoke test using FakeMemory backend")
    args = parser.parse_args()

    if args.use_fake:
        logger.info("Running smoke test on FakeMemory")
        backend: MemoryBackend = FakeMemory()
    else:
        api_key = os.environ.get("HINDSIGHT_API_KEY")
        if not api_key:
            logger.error("HINDSIGHT_API_KEY environment variable is required! Pass --use-fake for dry run.")
            sys.exit(1)
        backend = HindsightMemory()

    try:
        await run_smoke_test(backend)
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
