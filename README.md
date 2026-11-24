# Background workers

A reference pack provided by the pytemplate-hub maintainer.

Two starting points for a Python job worker: asyncio jobs with typed payloads, retries with
exponential backoff, a dead-letter list, per-job timeouts, and graceful shutdown on SIGINT and
SIGTERM. The `worker` profile keeps jobs in memory. The `worker-redis` profile adds a Redis queue,
chosen by `REDIS_URL`. Both ship with tests that need no broker.

## What you get

A generated `worker` project:

```
my-worker/
  pyproject.toml          # standard library only; uv_build; ruff, mypy strict, pytest
  README.md               # run the demo, use the worker, the behaviour and the checks
  AGENTS.md               # commands, layout, and rules for coding agents
  CLAUDE.md               # imports AGENTS.md
  my_worker/
    jobs.py               # Job and DeadLetter dataclasses; the Handler type
    queues.py             # Queue protocol and MemoryQueue
    worker.py             # Worker, WorkerConfig, retry backoff, install_signal_handlers
    handlers.py           # example greet handler that validates its payload
    app.py                # demo entry point behind `uv run my-worker`
  tests/
    test_worker.py        # success, retry, dead letter, timeout, unknown kind, shutdown
    test_handlers.py      # payload validation
```

The `worker-redis` profile has the same core, plus `redis_queue.py` (`RedisQueue`, on the asyncio
Redis client), `settings.py` (reads `REDIS_URL`), and `tests/test_redis_queue.py` and
`tests/test_settings.py`, which use `fakeredis`.

## Profiles

| Profile | Kind | Runtime dependencies | Queue | Tests need |
| --- | --- | --- | --- | --- |
| `worker` | service | none (standard library) | in memory | nothing |
| `worker-redis` | service | `redis>=5` | in memory, or Redis when `REDIS_URL` is set | nothing; Redis queue tested with `fakeredis` |

Each profile's `security_posture` states what the generated project needs and what it does not
check. Neither profile stores a secret.

## Create a project

```bash
uvx pytemplate-uv@latest create my-worker -p worker --template gh:yuxuzi/background-worker --template-ref v1.0.0 -y
uvx pytemplate-uv@latest create my-worker -p worker-redis --template gh:yuxuzi/background-worker --template-ref v1.0.0 -y
```

Then:

```bash
cd my-worker
uv run my-worker
```

## What the generated checks run

Each project runs these, in order: `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy <package> tests`, and `uv run pytest`. The tests run offline. The `worker-redis`
tests do not contact a Redis server: the Redis queue is tested against `fakeredis`, an in-process
fake, so real Redis was not part of the tests.

The checks do not scan dependencies or code for security problems, and they do not test handler
logic beyond what the examples cover.

## Customizing

Fork the repository, change the templates, and tag your own version. Generated projects record the
pack's source and tag, and you can pin the commit and digest with `--template-commit` and
`--template-digest`, as the hub's listing page shows.

## License

MIT. See [LICENSE](LICENSE).
