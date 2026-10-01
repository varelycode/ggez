# ggez

A development workflow kit for humans and coding agents.

Start with a blank Brief. Fill in **Slice** and **Outcome**, approve tasks, then build and review the result. Human-readable documents stay visible; generated task records live under `.ggez/`.

## Available now

- [Brief](templates/prd.md), [Tasks](templates/tasks.md), [Evidence](templates/evidence.md), and [Review](templates/review.md) templates.
- Ralph JSON examples and a Python helper that validates JSON and renders a readable view.
- [Working agreement](docs/workflow.md) and [agent rules](AGENTS.md).

The CLI and companion skill are not implemented. Neither are Markdown-to-JSON conversion, automatic drift detection, execution tracking, or token/time collection. The existing JSON renderer is an inspection helper; it must not overwrite the editable task document.

## Check the existing tools

Requires Python 3; no third-party dependencies.

```sh
python3 -B -m unittest discover -s tests -v
python3 scripts/tasks.py validate --root templates/ralph --allow-placeholders
```

## Planned interface

| Action | Purpose |
| --- | --- |
| `ggez init` | Preview and install project files and agent instructions |
| `ggez brief "Feature name"` | Create a blank Brief with only the title filled |
| `ggez status` | Show the active outcome, task, state, blockers, and usage |
| `ggez check` | Validate configuration, task IDs, and generated files |
| `ggez update` | Preview kit updates while preserving project changes |

One `ggez` skill will offer the same workflow through conversation. These commands are design requirements, not available commands.

## Planned project layout

```text
features/<feature-id>/
    brief.md
    tasks.md
    evidence.md
    review.md

.ggez/
    config.json
    templates/
    features/<feature-id>/
        tasks.json
        tasks/
        sync.json
        usage.jsonl
```

`tasks.md` is authoritative. Stable task IDs and content hashes will detect missing pairs and changed definitions. Evidence accumulates per task; Review accepts or revises the whole feature.

## Origin

Extracted from [Unisson](https://github.com/varelycode/unisson). Ralph JSON examples follow [PageAI Ralph Loop’s task format](https://github.com/PageAI-Pro/ralph-loop/blob/eba65ebbb0a78c4a7fd25aab28e94966eddbca5b/.agent/skills/prd-creator/JSON.md). The Markdown templates and validation helper are project adaptations. Ralph runner integration is unverified.
