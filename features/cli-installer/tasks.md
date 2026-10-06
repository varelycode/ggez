# Simple CLI installer — Tasks

Approved by Viviana on 2026-10-06. Keep TASK-N IDs stable. This is the editable task source; changes after approval require fresh approval.

**Brief:** [Approved Brief](brief.md)

**Evidence:** [Task results](evidence.md).

## Queue

- [x] TASK-1 — Verify project prerequisites and access

  - Done when: Python 3.9+, download tools, a disposable install location, and macOS/Linux test access are checked. Confirm how status reads evidence and timing without adding a runner; record missing prerequisites.
  - Verify: `python3 --version`, `git --version`, `command -v curl`, and `python3 -B -m unittest discover -s tests -v`. Confirm Linux execution access; do not substitute simulated platform checks.
  - Must not: Start implementation with blocked prerequisites or expose secrets.

  <details>
  <summary>Implementation details</summary>

  Read the approved Brief and current code. Create one feature Evidence record from the template and record prerequisite results. Agree any unresolved status-record contract before implementation.

  Category: setup

  </details>

- [x] TASK-2 — Install the CLI

  - Done when: A one-line install command installs a user-local `ggez` on macOS/Linux. Help works or gives the exact PATH step. Missing Python, failed downloads, permission errors, and reinstall attempts preserve an existing working installation.
  - Verify: Run installer integration tests in isolated home/install directories, including failure and repeat-install cases. Smoke-test `ggez --help` on macOS and Linux.
  - Must not: Require administrator access, silently edit shell configuration, or claim untested platforms work.
  - Depends on: TASK-1

  <details>
  <summary>Implementation details</summary>

  Add the CLI entry point and install script. Bundle required templates, validate installation before activation, and test failure recovery. Keep Python tools in scripts/ and tests in tests/.

  Category: functional

  </details>

- [x] TASK-3 — Initialize fresh and existing projects

  - Done when: `ggez init` previews changes and installs templates and scoped agent rules. Repeating it makes no duplicates. Existing instructions, edited templates, files, and Git history survive; conflicts are shown for resolution.
  - Verify: Integration tests cover empty/existing directories, repeated init, edited managed files, conflicting instructions, unsafe paths/symlinks, cancellation, and write failures. Compare unrelated files before and after.
  - Must not: Overwrite user edits, add a skill companion, or claim tracking/runner capabilities that do not exist.
  - Depends on: TASK-2

  <details>
  <summary>Implementation details</summary>

  Install the approved workflow, feature-level Evidence/Review, layout, snapshot/approval rules, and usage limitations. Include Verified as default and explicit Unverified behavior. Preserve edits; create neither an app nor a Git repository.

  Category: functional

  </details>

- [x] TASK-4 — Create or select a feature with plan

  - Done when: `ggez plan "Feature title"` creates a unique feature folder and blank Brief. No-title plan lists local features plus New feature. Selection prints the Brief path and handoff prompt; cancellation writes nothing.
  - Verify: Tests cover title-only creation, blank required fields, collisions, unsafe paths, empty/multiple-feature lists, selection, and cancellation. Inspect the prompt for both execution modes and human approval.
  - Must not: Fill required fields, infer approval, overwrite a feature, or launch an agent/runner.
  - Depends on: TASK-3

  <details>
  <summary>Implementation details</summary>

  Use the Brief template with only its title filled. Print a short loop overview and copyable agent prompt. Require the user to fill Slice and Outcome; allow requested help with optional sections. Keep selection within the current project.

  Category: functional

  </details>

- [x] TASK-5 — Report feature status from available evidence

  - Done when: Status selects one feature automatically or offers a choice. It shows goal, stage, task, state/reason, completion count/percentage, and recorded time. Missing data is explicit; Running needs a live signal and Complete needs checks plus human acceptance.
  - Verify: Tests cover every state/reason, no tasks, partial completion, missing/malformed evidence, absent/partial timing, excluded approval waits, multiple features, and stale run signals. Checkboxes alone cannot produce Complete.
  - Must not: Invent elapsed time, infer a live run from a stale timestamp, or implement a runner to supply missing data.
  - Depends on: TASK-4

  <details>
  <summary>Implementation details</summary>

  Use the record contract checked in TASK-1. Read existing documents/records without mutating them. Report unavailable execution time when no trustworthy timing exists. Keep errors short with a next step.

  Category: functional

  </details>

- [x] TASK-6 — Verify the walkthrough and README

  - Done when: README has tested one-line install/init/plan/status examples. Both project scenarios work offline after install. All acceptance checks have evidence and the feature Review is ready for Viviana.
  - Verify: `python3 -B -m unittest discover -s tests -v`; installer smoke tests on macOS/Linux; install → init → plan → status in disposable fresh/existing projects. Check Markdown limits and rollback preservation.
  - Must not: Add redundant docs, skip failed checks, mark human acceptance, merge, or open a PR.
  - Depends on: TASK-5

  <details>
  <summary>Implementation details</summary>

  Update the existing README and changed workflow references; remove stale claims only for implemented behavior. Check every Brief acceptance item against Evidence. Prepare one feature Review from its template; leave human acceptance unchecked.

  Category: functional

  </details>

## Execution rules

1. Start only after task approval. Work in order; test each task and append results, failures, and corrections to the same Evidence record.
2. Verified is the default: pause after each task for human review. Unverified requires explicit user instruction; tests, evidence, stop conditions, and final human acceptance still apply.
3. Stop on failures, missing prerequisites, or scope expansion. No runner JSON is needed for direct agent work.

## Status

**Next task:** None; review the outcome.

**Mode:** Unverified, requested by Viviana on 2026-10-06.

**Blocked by:** Final human acceptance pending; implementation is complete.
