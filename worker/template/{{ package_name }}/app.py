"""Demo entry point: enqueue a few jobs in memory, run them to completion, and print a summary."""

from __future__ import annotations

import asyncio
import logging

from .handlers import HANDLERS
from .jobs import Job
from .queues import MemoryQueue
from .worker import Worker, WorkerConfig, install_signal_handlers

DEMO_JOBS = (
    Job(kind="greet", payload={"name": "Ada"}),
    Job(kind="greet", payload={"name": "Grace"}),
    # Fails validation on every attempt, so it is dead-lettered after max_attempts.
    Job(kind="greet", payload={"name": "  "}),
    # No handler is registered for this kind, so it is dead-lettered at once.
    Job(kind="send-fax", payload={}),
)

DEMO_CONFIG = WorkerConfig(
    concurrency=2,
    job_timeout=5.0,
    max_attempts=3,
    backoff_base=0.1,
    poll_interval=0.05,
)


async def run_demo() -> int:
    """Run the demo jobs and return how many were dead-lettered."""
    queue = MemoryQueue()
    for job in DEMO_JOBS:
        await queue.put(job)
    worker = Worker(queue, HANDLERS, DEMO_CONFIG)
    install_signal_handlers(worker)
    await worker.run(drain=True)
    return len(await queue.dead_letters())


def main() -> None:
    """Run the demo and print how many jobs were dead-lettered."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    dead = asyncio.run(run_demo())
    print(f"demo finished: {len(DEMO_JOBS) - dead} done, {dead} dead-lettered")


if __name__ == "__main__":
    main()
