# Agent rules

ggez: a reusable workflow kit for humans and coding agents. Python 3 task helpers exist; the CLI, skill, converter, and runner are planned.

## Testing

- Test changes. Run tool tests with `python3 -B -m unittest discover -s tests -v`.
- Use sample notes.
- Never fake results.

## Documentation

- Use `templates/` for document formats.
- Apply no-ai-slop and i-have-adhd.
- Keep Markdown files under 600 characters, except for the exemptions below.
- `AGENTS.md` files have no length limit.
- The root `README.md` has no length limit.
- Everything in `templates/` is exempt from the length limit.

## Feature Workflow

- To start a feature, create a blank Brief from the template, retaining only the requested title. Leave all fields as placeholders; do not infer goals, scope, ownership, status, or acceptance checks.
- Mark Slice and Outcome as **Required** and ask the user to fill both sections in one handoff. Explain that the remaining sections may stay blank initially and approval comes after review.
- Do not default to a one-question-at-a-time interview. Offer help on request, and fill or propose sections only when asked. When clarification is needed, present a short, bounded set of missing details.
- Follow the [workflow](docs/workflow.md), approved Brief and tasks, and active issue.
- Show evidence and report blockers.
- Keep one `evidence.md` and one `review.md` per feature, alongside its Brief. Do not create separate Evidence or Review files for individual tasks.
- Append each task’s checks, results, failures, and corrections under its task ID in the feature’s `evidence.md`. In default mode, pause for human review of that evidence before continuing.
- Use the feature’s `review.md` to assess the complete outcome against the Brief and record the human’s final decision after all tasks finish. Task approval does not mean feature acceptance.
- Update [CHANGELOG.md](CHANGELOG.md) after each PRD/Brief/feature merge that completes an outcome: one entry per completed task set, not per task or commit. Include the date, delivered outcome, and merge PR or commit link. Record only merged work.
- Ask before expanding scope.
- Capture unrelated bugs and ideas as GitHub Issues labeled `backlog`. Check for duplicates first; include the source Brief/task and discovery context, then link the issue in Evidence. Keep the label as workflow provenance when work starts. Recording an issue does not approve implementation.
- Open PRs only when asked.
- Verify Ralph setup before running loops.

## Code and Data

- Keep tools in `scripts/` and tests in `tests/`.
- Follow existing Python style.
- Preserve edits.
- Never commit secrets.

## ggez Init Requirements

The CLI is planned; these are requirements for its implementation.

- Include the feature-level Evidence and Review, file layout, and usage tracking rules in the instructions installed by `ggez init`.
- Include those rules when adding instructions to an existing project `AGENTS.md`, even if no other kit files are installed. In that mode, document the layout without claiming directories or tracking have been created.
- Preview changes and preserve existing project instructions. Update an existing ggez section instead of duplicating it; surface conflicting rules for resolution.

## ggez Feature Layout

These are requirements for the planned CLI; this repository holds kit source templates in `templates/`; installation copies them into the destination project’s `.ggez/templates/`.

- Keep human-readable feature documents in `features/<feature-id>/`: `brief.md`, `tasks.md`, `evidence.md`, and `review.md`.
- Keep machine records in `.ggez/features/<feature-id>/`: `tasks.json`, `tasks/`, and usage records. Keep installed kit templates in `.ggez/templates/`.
- Use the same stable feature ID in both locations. Mirror the directories, not their contents. Human-edited `tasks.md` is the task source of truth; generate hidden Ralph JSON from it. Never overwrite it with a JSON rendering.
- Feature creation must establish both directories. Rename and archive operations must handle both together and preserve links and records; report incomplete operations.
- `ggez check` must validate paired directories, task IDs, references, and generated JSON freshness. Run this validation before execution; reconcile changes from Markdown and require approval of the resulting revision before running.
- Adapt and verify Ralph paths before execution; do not assume it accepts this layout without configuration.

## ggez Usage Tracking

These are requirements for the planned runner; usage collection is not implemented yet.

- Record each execution attempt under `.ggez/features/<feature-id>/usage.jsonl`, with a unique attempt ID, stage, optional task ID, runner/model, start and end times, outcome, and reported token counts.
- Track execution elapsed time separately from waiting for human approval. Include checks and tool execution within a run. Mark interrupted or incomplete timing as partial; do not count downtime after a lost runner as execution.
- Record input and output tokens only when the runtime supplies them. Show unavailable or partial coverage explicitly; never infer usage from text length or substitute account-wide totals. Keep cached-token counts separate when supplied and avoid double-counting them.
- Include failed attempts and retries in totals. Deduplicate repeated usage events and retain attempt history so expensive rework remains visible.
- Show per-task time, input/output tokens, and attempt count in `ggez status`, with feature totals and coverage. Attribute Brief, task-generation, and review runs to their stage rather than inventing a task ID.
- Report usage only for executions ggez can observe. Do not imply external chat or editor activity was measured. Keep prompts, document content, and credentials out of usage records.

## ggez Task Identity and Sync

The Markdown-to-JSON converter and drift checks are planned, not implemented. `scripts/tasks.py` currently only validates and renders JSON; its output must not replace editable task documents.

- Match tasks by `(feature ID, task ID)`. Use stable `TASK-N` IDs in Markdown, the JSON index, and individual task specs. Do not derive identity from titles, timestamps, or queue position. Never renumber or reuse an existing ID.
- Keep synchronization metadata in `.ggez/features/<feature-id>/sync.json`, outside Ralph's schema. Record task IDs, SHA-256 hashes of parsed task definitions, generated artifact hashes, converter version, generation time, and the approved task-set revision.
- Hash all execution-relevant task fields, including acceptance checks, steps, verification, boundaries, and dependencies. Include queue order in the task-set revision. Ignore only presentation differences defined by the parser; fail on ambiguous or unsupported content rather than silently dropping it.
- A missing pair is an unsynchronized addition or removal; a matching ID with a different hash is changed content. Duplicate IDs, broken dependencies, and manually changed generated JSON also block execution. Timestamps are informational, not proof of a match.
- Before execution, validate Markdown and regenerate derived JSON as one complete revision. Show added, changed, and removed tasks for approval; never reconcile by overwriting the human document. A failed conversion must leave the previous complete generation intact and block running stale files.
- Keep completion, attempts, and usage in separate machine records keyed by task ID and definition revision. Regeneration must preserve history. Changed tasks and affected dependents require review and re-verification; removed tasks retain history but leave the runnable queue. Markdown checkboxes alone cannot establish verified completion.
- Run an immutable snapshot of the approved revision. Edits during execution do not change the active task; pause before starting another task when the source revision changes. Retain results against the revision actually executed.
- `ggez init` must include these source, identity, and synchronization rules in new or existing project agent instructions, including instructions-only installs.

## CLI and Skill Discovery

- Provide one entry point named `ggez`. The planned companion skill handles “start a feature,” “prepare tasks,” “build it,” and status requests.
- Installation should set up the CLI and offer the skill. `ggez init` should add discoverable instructions to existing agent files without overwriting them.
- Bare `ggez` should show the current feature and next action; outside an initialized project, offer setup. Keep help focused on the main actions with examples.
- Keep template-only use possible. Explain which validation and tracking capabilities are unavailable without the tooling; do not claim instructions enforce them.

## Status

- Use four states only: `Ready`, `Running`, `Needs attention`, and `Complete`.
- For `Needs attention`, use fixed reasons: `Approval required`, `Check failed`, `Missing prerequisite`, or `Run interrupted`.
- Stage is separate: `Brief`, `Tasks`, `Implementation`, or `Review`. Display Current task, Stage and completion count, Outcome, State/reason, then human-readable file links.
- Derive transitions from recorded events. `Running` requires a live runner signal. `Complete` requires all required checks and human acceptance of the outcome; finishing implementation alone leads to Review with approval required.
