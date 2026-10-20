# Agent rules

ggez: a reusable workflow kit for humans and coding agents. Python 3 task helpers, a user-local installer, and CLI init/plan/status/update exist. The skill, converter, and runner are planned.

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
- Report checks and blockers in the active agent run or pull request.
- Keep `brief.md` and `tasks.md` per feature. Each task has exactly one Result: `Pending`, `Pass`, `Fail`, `Blocked`, or `Interrupted`; check it exactly when Result is `Pass`.
- In default mode, test one task, update its Result, then pause for human review. Unverified mode requires explicit user instruction and skips only those pauses.
- Assess the complete outcome against the Brief acceptance checks. Only the user checks final acceptance; task approval does not mean feature acceptance.
- Update [CHANGELOG.md](CHANGELOG.md) after each PRD/Brief/feature merge that completes an outcome: one entry per completed task set, not per task or commit. Include the date, delivered outcome, and merge PR or commit link. Record only merged work.
- Ask before expanding scope.
- Capture unrelated bugs and ideas as GitHub Issues labeled `backlog`. Check for duplicates first; include the source Brief/task and discovery context, then link the issue from the active task. Keep the label as workflow provenance when work starts. Recording an issue does not approve implementation.
- Open PRs only when asked.
- Verify Ralph setup before running loops.

## Code and Data

- Keep tools in `scripts/` and tests in `tests/`.
- Follow existing Python style.
- Preserve edits.
- Never commit secrets.

## ggez Init Requirements

Init installs templates and managed workflow instructions. Plan creates blank Briefs; status reads recorded progress.

- Include the Brief/Tasks layout, fixed task Results, acceptance checks, and usage tracking rules in the instructions installed by `ggez init`.
- Include those rules when adding instructions to an existing project `AGENTS.md`, even if no other kit files are installed. In that mode, document the layout without claiming directories or tracking have been created.
- Preview changes and preserve existing project instructions. Update an existing ggez section instead of duplicating it; surface conflicting rules for resolution.

## ggez Feature Layout

Kit source templates live in `templates/`; init copies document templates to `.ggez/templates/`. Runner integration remains planned.

- Keep editable documents in `features/<feature-id>/`: `brief.md` and `tasks.md`.
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
- Record completion, task Results, and usage against the run and task IDs. Preserve previous attempts. Carry verified progress into a revised run only after confirming the task and its prerequisites still satisfy the revised requirements.
- Direct agent work can use the approved Markdown without Ralph JSON. The approval and Result rules still apply.
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
- Derive transitions from task Results and Brief acceptance checks. `Running` requires a live runner signal. `Complete` requires every task checked with Result `Pass` and every acceptance check checked; finishing implementation alone leads to Review with approval required.

<!-- ggez:start -->
## ggez workflow

- Use `ggez plan "Feature title"` for a blank Brief, `ggez plan` to select a feature, `ggez status` to read recorded progress, and `ggez update` to update an installed CLI. These commands do not run an agent.

- Use `.ggez/templates/` for feature documents. Start a blank Brief with only its requested title. The user fills Slice and Outcome; never fill those required sections. Explain fields when asked and propose optional sections only on request.
- Before preparing tasks, require Context with one to five direct paths or URLs and a reason for each, or exactly `None beyond AGENTS.md and this Brief`. Read those sources. Do not load references found inside them unless the work requires it. Invalid or placeholder Context stays at Brief approval.
- Keep `brief.md` and `tasks.md` in `features/<feature-id>/`. Create the feature folder when planning starts. Keep stable feature and TASK-N IDs.
- Get human approval of the Brief, then the exact Markdown task list, before implementation. `tasks.md` is the editable task source. Changed instructions need fresh approval; never reuse approval for a changed task set.
- Each task has exactly one Result: `Pending`, `Pass`, `Fail`, `Blocked`, or `Interrupted`. Check a task exactly when its Result is `Pass`.
- Verified is the default: execute one approved task, test it, update its Result, then wait for human review. Unverified requires explicit user instruction and skips per-task review only. Tests, stop conditions, and final human acceptance still apply.
- Stop on failures, blockers, or scope expansion. Keep secrets out of documents. Follow existing project conventions; surface conflicting rules for resolution before working.
- Report checks, failures, and corrections in the active agent run or pull request. Do not create another workflow document for them.
- Assess the full outcome against the Brief acceptance checks. Only the user checks final acceptance; finishing tasks does not mean the user accepted the feature.
- Direct agent work uses approved Markdown. This CLI does not launch or supervise a runner. Automatic conversion, run snapshots, usage collection, and the companion skill are unavailable.
- If a separately verified Ralph integration is used, keep its fixed approved Markdown, approval record, and complete generated inputs under `.ggez/features/<feature-id>/runs/<run-id>/`. Validate inputs and dependencies before execution; stop if conversion fails. Later edits need a newly approved snapshot. Preserve prior runs; never synchronize edits into an active run.
- Usage records, when supplied by an execution system, belong in `.ggez/features/<feature-id>/usage.jsonl`. Keep unique attempt IDs, stage/task IDs, runner/model, start/end times, outcomes, and reported token counts. Include retries, deduplicate events, separate execution from approval waits, mark partial timing, and keep cached tokens separate. Never estimate tokens or substitute account totals. Missing data is unavailable; these instructions do not collect usage.
- Status counts a task only when it is checked with Result `Pass`; inconsistent task state is invalid. Complete requires every task to pass and every Brief acceptance check to be checked. Optional usage records report execution_seconds excluding approval waits and timing_complete; missing timing is unavailable. Duplicate attempt IDs must agree.
- State is Ready, Running, Needs attention, or Complete; stage is Brief, Tasks, Implementation, or Review. Needs attention reasons are Approval required, Check failed, Missing prerequisite, or Run interrupted. Running requires a live signal; Complete requires checks and human acceptance. Checkboxes alone prove neither.
<!-- ggez:end -->
