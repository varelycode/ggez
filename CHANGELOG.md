# Changelog

## 2026-11-13

- Added immutable Brief and task revision lineage, revision commands, stale-task checks, and clearer CLI structure. [PR #3](https://github.com/varelycode/ggez/pull/3).

## 2026-10-20

- Removed Evidence/Review and added Results plus `ggez update`. [#2](https://github.com/varelycode/ggez/pull/2).

## 2026-10-06

- Added the installer and init, plan, and status commands. [PR #1](https://github.com/varelycode/ggez/pull/1).

## 2026-10-01

- Extracted reusable workflow templates, task validation/rendering helpers, tests, and agreed CLI requirements from Unisson. CLI and skill implementation remain pending.

- Simplified task execution: approve Markdown first, then generate a fixed runner snapshot when needed. Removed ongoing sync requirements.
