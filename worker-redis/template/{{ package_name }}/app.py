"""Demo entry point: run the demo jobs on Redis when REDIS_URL is set, otherwise in memory."""

from __future__ import annotations

import asyncio
import logging

from redis.asyncio import Redis

from .handlers import HANDLERS
from .jobs import Job
from .queues import MemoryQueue, Queue
from .redis_queue import RedisQueue
from .settings import redis_url_from_env
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

log = logging.getLogger(__name__)


async def _run_jobs(queue: Queue) -> int:
    for job in DEMO_JOBS:
        await queue.put(job)
    worker = Worker(queue, HANDLERS, DEMO_CONFIG)
    install_signal_handlers(worker)
    await worker.run(drain=True)
    return len(await queue.dead_letters())


async def run_demo() -> int:
    """Run the demo jobs and return how many were dead-lettered."""
    url = redis_url_from_env()
    if url is None:
        log.info("event=queue_selected backend=memory")
        return await _run_jobs(MemoryQueue())
    log.info("event=queue_selected backend=redis")
    client = Redis.from_url(url)
    try:
        return await _run_jobs(RedisQueue(client))
    finally:
        await client.aclose()


def main() -> None:
    """Run the demo and print how many jobs were dead-lettered."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    dead = asyncio.run(run_demo())
    print(f"demo finished: {len(DEMO_JOBS) - dead} done, {dead} dead-lettered")


if __name__ == "__main__":
    main()
