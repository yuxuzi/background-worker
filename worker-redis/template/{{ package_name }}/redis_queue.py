"""A Redis-backed queue: a ready list, a processing list, and a dead-letter list.

Jobs are stored as JSON strings. ``get`` moves a job from the ready list to the processing list
and ``ack`` removes it again, so a job is not lost when a worker dies while it runs. Nothing here
moves jobs back from the processing list after a crash; that needs a recovery step this pack does
not include.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from .jobs import DeadLetter, Job


def _text(value: bytes | str) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _encode(job: Job) -> str:
    """Serialize a job with sorted keys, so the same job always gives the same string."""
    return json.dumps(
        {
            "id": job.id,
            "kind": job.kind,
            "attempts": job.attempts,
            "payload": dict(job.payload),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _decode(raw: str) -> Job:
    data: dict[str, Any] = json.loads(raw)
    return Job(
        kind=str(data["kind"]),
        payload=dict(data["payload"]),
        id=str(data["id"]),
        attempts=int(data["attempts"]),
    )


class RedisQueue:
    """A queue on a Redis server, usable by several worker processes at once.

    ``get`` blocks for up to ``timeout`` seconds with BLMOVE, which needs Redis 6.0 or later for
    fractional timeouts. Keys are ``<name>:ready``, ``<name>:processing``, and ``<name>:dead``.
    """

    def __init__(self, client: Redis, name: str = "jobs") -> None:
        self._client = client
        self._ready = f"{name}:ready"
        self._processing = f"{name}:processing"
        self._dead = f"{name}:dead"

    async def put(self, job: Job) -> None:
        """Add a job to the ready list."""
        await self._client.lpush(self._ready, _encode(job))

    async def get(self, timeout: float) -> Job | None:
        """Move the oldest job to the processing list, or return None after ``timeout`` seconds."""
        # redis-py types the timeout as int; Redis 6.0+ accepts fractional seconds.
        raw = await self._client.blmove(
            self._ready,
            self._processing,
            timeout,  # type: ignore[arg-type]
            src="RIGHT",
            dest="LEFT",
        )
        if raw is None:
            return None
        return _decode(_text(raw))

    async def ack(self, job: Job) -> None:
        """Remove a job from the processing list."""
        await self._client.lrem(self._processing, 1, _encode(job))

    async def dead_letter(self, job: Job, error: str) -> None:
        """Keep a job and its error in the dead-letter list."""
        record = json.dumps({"job": _encode(job), "error": error}, sort_keys=True)
        await self._client.lpush(self._dead, record)

    async def dead_letters(self) -> list[DeadLetter]:
        """Return the dead-lettered jobs, oldest first."""
        raws = await self._client.lrange(self._dead, 0, -1)
        letters: list[DeadLetter] = []
        for raw in reversed(raws):
            data: dict[str, Any] = json.loads(_text(raw))
            letters.append(DeadLetter(job=_decode(str(data["job"])), error=str(data["error"])))
        return letters
