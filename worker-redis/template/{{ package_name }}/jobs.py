"""Job model: what a queue carries and what a handler receives."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class Job:
    """One unit of work.

    ``payload`` is untrusted input, so handlers must validate every field they use. ``attempts``
    counts the attempts already made; the worker increments it when it schedules a retry.
    """

    kind: str
    payload: Mapping[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    attempts: int = 0


@dataclass(frozen=True)
class DeadLetter:
    """A job that used its last attempt, with the error text of that attempt."""

    job: Job
    error: str


Handler = Callable[[Job], Awaitable[None]]
"""An async function that does one job. It raises to signal a failed attempt."""
