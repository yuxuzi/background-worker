"""The queue port and its in-memory implementation."""

from __future__ import annotations

import asyncio
from typing import Protocol

from .jobs import DeadLetter, Job


class Queue(Protocol):
    """Where jobs wait between being enqueued and being run.

    ``get`` waits at most ``timeout`` seconds and returns None when nothing arrived. ``ack`` marks a
    job taken by ``get`` as finished, and is called once per job, whatever the outcome.
    """

    async def put(self, job: Job) -> None:
        """Add a job to the queue."""

    async def get(self, timeout: float) -> Job | None:
        """Take the next job, or return None after ``timeout`` seconds."""

    async def ack(self, job: Job) -> None:
        """Mark a job taken by ``get`` as finished."""

    async def dead_letter(self, job: Job, error: str) -> None:
        """Keep a job that failed its last attempt, with the error text."""

    async def dead_letters(self) -> list[DeadLetter]:
        """Return the dead-lettered jobs, oldest first."""


class MemoryQueue:
    """A queue inside one process. Jobs are lost when the process exits."""

    def __init__(self) -> None:
        self._ready: asyncio.Queue[Job] = asyncio.Queue()
        self._dead: list[DeadLetter] = []

    async def put(self, job: Job) -> None:
        """Add a job to the queue."""
        await self._ready.put(job)

    async def get(self, timeout: float) -> Job | None:
        """Take the next job, or return None after ``timeout`` seconds."""
        try:
            return await asyncio.wait_for(self._ready.get(), timeout)
        except TimeoutError:
            return None

    async def ack(self, job: Job) -> None:
        """Nothing to do: a job taken from memory is already gone from the queue."""

    async def dead_letter(self, job: Job, error: str) -> None:
        """Keep a job that failed its last attempt, with the error text."""
        self._dead.append(DeadLetter(job=job, error=error))

    async def dead_letters(self) -> list[DeadLetter]:
        """Return the dead-lettered jobs, oldest first."""
        return list(self._dead)

    def pending(self) -> int:
        """Return how many jobs are waiting to be taken."""
        return self._ready.qsize()
