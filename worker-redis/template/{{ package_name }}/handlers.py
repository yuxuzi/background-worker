"""Example job handlers. Payloads are untrusted: check every field before use."""

from __future__ import annotations

import json
import logging

from .jobs import Handler, Job

log = logging.getLogger(__name__)

MAX_NAME_LENGTH = 100


async def greet(job: Job) -> None:
    """Log a greeting for ``payload["name"]``, which must be a non-blank string."""
    name = job.payload.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME_LENGTH:
        raise ValueError(
            f"payload.name must be a non-blank string of at most {MAX_NAME_LENGTH} characters"
        )
    log.info("event=greeted name=%s", json.dumps(name))


HANDLERS: dict[str, Handler] = {"greet": greet}
"""The handlers the demo registers, by job kind."""
