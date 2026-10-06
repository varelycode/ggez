# Agent rules

ggez: a reusable workflow kit for humans and coding agents. Python 3 task helpers, a user-local installer, and CLI init/plan/status exist. The skill, converter, and runner are planned.

## Testing

- Test changes. Run tool tests with `python3 -B -m unittest discover -s tests -v`.
- Use sample notes.
- Never fake results.

## Documentation

- Use `templates/` for document formats.
- Apply no-ai-slop and i-have-adhd.
- Keep Markdown files under 600 characters, except for the exemptions below.
- `AGENTS.md` files have no length limit.
- Keep this repository’s root `README.md` under 1,000 characters.
- Everything in `templates/` is exempt from the length limit.

## Feature Workflow

- To start a feature, create a blank Brief from the template, retaining only the requested title. Leave all fields as placeholders; do not infer goals, scope, ownership, status, or acceptance checks.
- Mark Slice and Outcome as **Required** and ask the user to fill both sections in one handoff. Explain that the remaining sections may stay blank initially and approval comes after review.
- Do not default to a one-question-at-a-time interview. Explain required fields on request, but never fill Slice or Outcome. Fill or propose optional sections only when asked. When clarification is needed, present a short, bounded set of missing details.
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

Init installs templates and managed workflow instructions. Plan creates blank Briefs; status reads recorded progress.

- Include the feature-level Evidence and Review, file layout, and usage tracking rules in the instructions installed by `ggez init`.
- Include those rules when adding instructions to an existing project `AGENTS.md`, even if no other kit files are installed. In that mode, document the layout without claiming directories or tracking have been created.
- Preview changes and preserve existing project instructions. Update an existing ggez section instead of duplicating it; surface conflicting rules for resolution.

## ggez Feature Layout

Kit source templates live in `templates/`; init copies document templates to `.ggez/templates/`. Runner integration remains planned.

- Keep editable documents in `features/<feature-id>/`: `brief.md`, `tasks.md`, `evidence.md`, and `review.md`.
- Create the visible feature folder when starting a feature. Drafts need no corresponding machine task files or paired directory checks.
- When an approved task set is executed through Ralph, generate its JSON index and task specs under `.ggez/features/<feature-id>/runs/<run-id>/`. Configure Ralph to consume that run's files and verify the integration before execution.
- Keep run records and usage separate from editable documents. Retain stable feature and task IDs so results can be traced to their source; preserve historical run paths when renaming display titles.

## ggez Usage Tracking

These are requirements for the planned runner; usage collection is not implemented yet.

- Record each execution attempt under `.ggez/features/<feature-id>/usage.jsonl`, with a unique attempt ID, stage, optional task ID, runner/model, start and end times, outcome, and reported token counts.
- Track execution elapsed time separately from waiting for human approval. Include checks and tool execution within a run. Mark interrupted or incomplete timing as partial; do not count downtime after a lost runner as execution.
- Record input and output tokens only when the runtime supplies them. Show unavailable or partial coverage explicitly; never infer usage from text length or substitute account-wide totals. Keep cached-token counts separate when supplied and avoid double-counting them.
- Include failed attempts and retries in totals. Deduplicate repeated usage events and retain attempt history so expensive rework remains visible.
- Show per-task time, input/output tokens, and attempt count in `ggez status`, with feature totals and coverage. Attribute Brief, task-generation, and review runs to their stage rather than inventing a task ID.
- Report usage only for executions ggez can observe. Do not imply external chat or editor activity was measured. Keep prompts, document content, and credentials out of usage records.

## Approved Task Snapshots

Automatic conversion and run snapshots are planned. `scripts/tasks.py` currently validates and renders JSON only; it must not overwrite editable task documents.

- `tasks.md` is the only editable task definition. Use stable `TASK-N` IDs; do not renumber or reuse them. There is no ongoing Markdown/JSON synchronization and no `sync.json`.
- Approve the exact task document before generating runner files. At launch, use that approved copy, validate required fields and dependencies, and generate the entire runner input together. If conversion fails or omits instructions, do not start execution.
- Keep the approved Markdown copy with its run ID, approval record, and generated JSON. The runner reads this fixed copy; its completion flags may change, but its task definitions must not. Users never edit or reconcile generated files.
- Later edits are a new draft. They do not alter the active run. Before continuing with those edits, pause at a task boundary, approve the revised document, and create a new run snapshot. Never apply old approval automatically to changed instructions.
- Record completion, evidence, and usage against the run and task IDs. Preserve previous attempts. Carry verified progress into a revised run only after confirming the task and its prerequisites still satisfy the revised requirements.
- Direct agent work can use the approved Markdown without Ralph JSON. The approval and evidence rules still apply.
- `ggez check` validates the documents and any selected run's internal consistency; it must not compare an old snapshot with a newer draft as a sync error.
- `ggez init` must include these rules in both new and existing agent instructions, including instructions-only installs.

## CLI and Skill Discovery

- Provide one entry point named `ggez`. The planned companion skill handles “start a feature,” “prepare tasks,” “build it,” and status requests.
- Installation sets up the CLI; the companion skill is out of scope for this release. `ggez init` should add discoverable instructions to existing agent files without overwriting them.
- Bare `ggez` should show the current feature and next action; outside an initialized project, offer setup. Keep help focused on the main actions with examples.
- Keep template-only use possible. Explain which validation and tracking capabilities are unavailable without the tooling; do not claim instructions enforce them.

## Status

- Use four states only: `Ready`, `Running`, `Needs attention`, and `Complete`.
- For `Needs attention`, use fixed reasons: `Approval required`, `Check failed`, `Missing prerequisite`, or `Run interrupted`.
- Stage is separate: `Brief`, `Tasks`, `Implementation`, or `Review`. Display Feature, Current task, Stage, completion count/percentage, recorded time, and full file paths. Keep Goal, State, and Next out of printed status output; retain the state rules internally.
- Derive transitions from recorded events. `Running` requires a live runner signal. `Complete` requires all required checks and human acceptance of the outcome; finishing implementation alone leads to Review with approval required.
