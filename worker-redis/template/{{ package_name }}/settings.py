"""Settings read from the environment.

``REDIS_URL`` may contain a password. It is read here and passed on to the Redis client; it is
never logged, printed, or included in an error message.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

REDIS_URL_VARIABLE = "REDIS_URL"
_SCHEMES = ("redis://", "rediss://", "unix://")


def redis_url_from_env(env: Mapping[str, str] | None = None) -> str | None:
    """Return ``REDIS_URL`` if it is set and not blank, otherwise None.

    Raises ValueError for a URL with an unknown scheme. The message does not include the URL.
    """
    source = os.environ if env is None else env
    value = source.get(REDIS_URL_VARIABLE, "").strip()
    if not value:
        return None
    if not value.startswith(_SCHEMES):
        raise ValueError(
            f"{REDIS_URL_VARIABLE} must start with redis://, rediss://, or unix:// "
            "(the value is not shown)"
        )
    return value
