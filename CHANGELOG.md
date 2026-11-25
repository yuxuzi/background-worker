# Changelog

All notable changes to the Background workers pack are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the pack follows semantic versioning.

## [1.1.0]

- The manifest declares `categories` and `keywords` for pytemplate-hub's filters and search
  (needs pytemplate-uv 3.4 or later).
- The README creates projects with the hub's short `-h yuxuzi/background-worker@v1.1.0` command.

## [1.0.0]

- Initial release: `worker` (in-memory queue) and `worker-redis` (Redis queue selected by
  `REDIS_URL`) profiles.
