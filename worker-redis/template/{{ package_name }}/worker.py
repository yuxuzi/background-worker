"""The worker loop: concurrency, timeouts, retries with backoff, dead letters, and shutdown."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from .jobs import Handler, Job
from .queues import Queue

log = logging.getLogger(__name__)


def _log(event: str, **fields: Any) -> None:
    """Write one structured line: ``event=<name> key="value" ...``. Values are JSON-quoted."""
    pairs = " ".join(f"{key}={json.dumps(value, default=str)}" for key, value in fields.items())
    log.info("event=%s %s", event, pairs)


@dataclass(frozen=True)
class WorkerConfig:
    """Worker limits. The defaults suit short jobs; tests inject a tiny ``backoff_base``.

    ``max_attempts`` counts the first attempt, so 3 means one try and two retries.
    """

    concurrency: int = 4
    job_timeout: float = 30.0
    max_attempts: int = 3
    backoff_base: float = 1.0
    max_backoff: float = 60.0
    poll_interval: float = 1.0

    def __post_init__(self) -> None:
        if self.concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.job_timeout <= 0 or self.poll_interval <= 0:
            raise ValueError("job_timeout and poll_interval must be greater than zero")
        if self.backoff_base < 0 or self.max_backoff < 0:
            raise ValueError("backoff_base and max_backoff must not be negative")

    def backoff(self, retry: int) -> float:
        """Return the seconds to wait before retry number ``retry`` (1 for the first retry)."""
        return min(self.max_backoff, self.backoff_base * 2.0 ** (retry - 1))


class Worker:
    """Runs jobs from a queue with a fixed number of concurrent consumers."""

    def __init__(
        self,
        queue: Queue,
        handlers: Mapping[str, Handler],
        config: WorkerConfig | None = None,
    ) -> None:
        self._queue = queue
        self._handlers = dict(handlers)
        self._config = config or WorkerConfig()
        self._stop = asyncio.Event()
        self._busy = 0

    def request_stop(self) -> None:
        """Stop taking new jobs. Jobs already running finish, then ``run`` returns."""
        _log("shutdown_requested", in_flight=self._busy)
        self._stop.set()

    async def run(self, drain: bool = False) -> None:
        """Run jobs until ``request_stop`` is called.

        With ``drain``, also return once the queue has been empty for a poll interval and no job is
        in flight. Jobs still queued when the worker stops stay in the queue.
        """
        _log("worker_started", concurrency=self._config.concurrency, drain=drain)
        consumers = [
            asyncio.create_task(self._consume(drain), name=f"consumer-{index}")
            for index in range(self._config.concurrency)
        ]
        try:
            await asyncio.gather(*consumers)
        except BaseException:
            for task in consumers:
                task.cancel()
            raise
        _log("worker_stopped", in_flight=self._busy)

    async def _consume(self, drain: bool) -> None:
        while not self._stop.is_set():
            job = await self._queue.get(self._config.poll_interval)
            if job is None:
                if drain and self._busy == 0:
                    return
                continue
            await self._process(job)

    async def _process(self, job: Job) -> None:
        self._busy += 1
        try:
            await self._attempt(job)
        finally:
            self._busy -= 1

    async def _attempt(self, job: Job) -> None:
        handler = self._handlers.get(job.kind)
        if handler is None:
            await self._fail(job, f"no handler for kind {job.kind!r}", "no_handler", retry=False)
            return
        try:
            await asyncio.wait_for(handler(job), self._config.job_timeout)
        except TimeoutError:
            await self._fail(job, f"timed out after {self._config.job_timeout}s", "timeout")
        except Exception as exc:
            await self._fail(job, f"{type(exc).__name__}: {exc}", "error")
        else:
            await self._queue.ack(job)
            _log("job_done", id=job.id, kind=job.kind, attempts=job.attempts + 1)

    async def _fail(self, job: Job, error: str, reason: str, *, retry: bool = True) -> None:
        attempts = job.attempts + 1
        if not retry or attempts >= self._config.max_attempts:
            await self._queue.dead_letter(replace(job, attempts=attempts), error)
            await self._queue.ack(job)
            _log("job_dead_lettered", id=job.id, kind=job.kind, attempts=attempts, reason=reason)
            return
        delay = self._config.backoff(attempts)
        _log(
            "job_retry_scheduled",
            id=job.id,
            kind=job.kind,
            attempts=attempts,
            reason=reason,
            delay=delay,
        )
        await asyncio.sleep(delay)
        # Put the retry before acking the failed attempt, so a crash cannot lose the job.
        await self._queue.put(replace(job, attempts=attempts))
        await self._queue.ack(job)


def install_signal_handlers(worker: Worker) -> None:
    """Call ``worker.request_stop`` on SIGINT or SIGTERM. Must be called from the running loop.

    A second signal does not force an exit: send SIGKILL to stop a worker that will not drain.
    Where the platform cannot add handlers (Windows), the worker still runs and logs that it could
    not.
    """
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except (NotImplementedError, RuntimeError):
            _log("signal_handler_unavailable", signal=sig.name)
