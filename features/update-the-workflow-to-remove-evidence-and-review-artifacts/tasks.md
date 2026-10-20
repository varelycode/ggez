# Simplify workflow artifacts and add CLI updates — Tasks

> This is the editable task source. Keep TASK-N IDs stable. Approve this exact document before implementation; later edits require fresh approval.

**Brief:** [Approved Brief](brief.md)

**Approval:** Viviana, 2026-10-16

## Queue

- [x] TASK-1 — Verify the baseline and upgrade contract

  - **Result:** Pass
  - Done when: The current tests, install layout, manifest format, and managed files are verified. The implementation has a bounded migration path from the four-template installation to the two-template installation.
  - Verify: `python3 --version`; `python3 -B -m unittest discover -s tests -v`; inspect `.ggez/install.json`, the active launcher, and a disposable initialized project.
  - Must not: Modify installed files, delete workflow documents, use live network access, or begin implementation while the baseline fails.

  <details>
  <summary>Implementation details</summary>

  Confirm the version-1 manifest records four templates and `AGENTS.md`. Identify every write, rollback, and validation path affected by removing managed templates. Use disposable directories for install and init checks.

  Category: setup
  Complexity: low

  </details>

- [x] TASK-2 — Migrate initialization to Brief and Tasks only

  - **Result:** Pass
  - Done when: Fresh initialization installs only `prd.md` and `tasks.md`. Reinitializing a four-template project removes unchanged managed Evidence and Review templates, upgrades the manifest, and preserves third-party feature documents and user edits.
  - Verify: Focused init tests cover fresh installs, old-manifest upgrades, edited legacy templates, missing legacy templates, repeated init, preview accuracy, cancellation, and rollback after a staged write or deletion fails.
  - Must not: Delete third-party feature documents, overwrite edited templates, accept malformed manifests, or leave a partially upgraded project.
  - Depends on: TASK-1

  <details>
  <summary>Implementation details</summary>

  Reduce the managed template set in `scripts/ggez.py` and `scripts/install.py`. Add an explicit migration for the current manifest instead of weakening manifest validation. Extend the transactional init path to remove only files whose recorded hashes still match.

  Category: functional
  Complexity: high

  </details>

- [x] TASK-3 — Derive status from task Results and Brief acceptance

  - **Result:** Pass
  - Done when: Each task has exactly one Result from `Pending`, `Pass`, `Fail`, `Blocked`, or `Interrupted`. Status uses only the approved Brief and task list, rejects inconsistent task states, and reports Complete only after all tasks pass and every Brief acceptance check is checked.
  - Verify: Status tests cover every Result mapping, duplicate or missing Results, checked non-Pass tasks, unchecked Pass tasks, incomplete acceptance checks, full completion, missing tasks, approvals, multiple features, and the absence of Evidence and Review files.
  - Must not: Infer results from prose, treat checkboxes alone as proof, report Running without a live runner signal, or require a replacement artifact.
  - Depends on: TASK-2

  <details>
  <summary>Implementation details</summary>

  Parse Result within each task block. Map `Fail` to `Check failed`, `Blocked` to `Missing prerequisite`, and `Interrupted` to `Run interrupted`; map `Pending` to Ready after approvals. Count only checked tasks with Result `Pass`. Keep Review as a stage, not a document.

  Category: functional
  Complexity: high

  </details>

- [x] TASK-4 — Add an atomic `ggez update` command

  - **Result:** Pass
  - Done when: An installed `ggez update` downloads the same official archive used by the installer, validates the full payload, activates it in the current installation prefix, and reports whether the active release changed. Any failure leaves the previous launcher usable.
  - Verify: Installer and CLI tests cover update, already-current, download failure, malformed archive, incomplete payload, edited release, activation failure, paths with spaces, and invocation outside a managed installation. Use local fixtures or mocked downloads.
  - Must not: Require a source checkout, update a different prefix, replace an unrelated launcher, edit shell configuration, or activate an unchecked release.
  - Depends on: TASK-2

  <details>
  <summary>Implementation details</summary>

  Include the updater in installed release payloads and reuse the installer’s validation and atomic launcher replacement. Resolve the prefix from the managed installation and reject ambiguous source-checkout invocation with a short recovery message.

  Category: functional
  Complexity: high

  </details>

- [x] TASK-5 — Align prompts, templates, rules, and documentation

  - **Result:** Pass
  - Done when: CLI help and handoffs, managed agent rules, Brief and task templates, task rendering, Ralph fixtures, README, workflow documentation, and this repository's `AGENTS.md` describe the Brief-and-Tasks workflow and `ggez update` without asking for Evidence or Review artifacts.
  - Verify: Focused plan, task-rendering, workflow, and installer tests pass. Search user-facing sources for stale Evidence or Review instructions and inspect every intentional legacy reference retained for migration tests.
  - Must not: Remove migration compatibility, claim runner or usage capabilities that do not exist, exceed the repository's Markdown limits, or rewrite unrelated project instructions.
  - Depends on: TASK-3, TASK-4

  <details>
  <summary>Implementation details</summary>

  Add the fixed Result field to task sources and generated task Markdown. Remove Evidence and Review links from the Brief template. Keep test output in the terminal, agent chat, or pull request. Update README examples for install, update, init, plan, and status.

  Category: documentation
  Complexity: medium

  </details>

- [x] TASK-6 — Remove repository artifacts and verify the full workflow

  - **Result:** Pass
  - Done when: This repository contains no feature-level `evidence.md` or `review.md` documents and no active Evidence or Review templates. The full local install, update, init, plan, task, and status workflow satisfies every Brief acceptance check.
  - Verify: `python3 -B -m unittest discover -s tests -v`; `git diff --check`; install to a disposable prefix; exercise fresh and upgraded disposable projects; run `ggez update` against a controlled archive; inspect changed Markdown and all Brief acceptance checks.
  - Must not: Delete third-party documents, use the user's live installation for destructive tests, mark Viviana's final acceptance checkbox, open a pull request, or merge.
  - Depends on: TASK-5

  <details>
  <summary>Implementation details</summary>

  Delete repository-owned Evidence and Review feature documents only after their replacement status behavior and migration tests pass. Remove obsolete templates. Preserve Git history as the recovery path and leave final acceptance to Viviana.

  Category: verification
  Complexity: medium

  </details>

## Execution rules

1. Start only after Viviana approves this exact task document. Execute tasks in ID order unless dependencies require a stop.
2. After each task, run its checks. Set Result to `Pass` and check the task only when every required check passes, then pause for Viviana's review.
3. Set Result to `Fail`, `Blocked`, or `Interrupted` when that exact condition occurs. Report the command and relevant output in chat; do not create an Evidence file.
4. Stop on failed checks, missing prerequisites, scope expansion, inconsistent state, or any risk to an existing installation.

## Status

**Next task:** TASK-1 — Verify the baseline and upgrade contract

**Mode:** Unverified, requested by Viviana on 2026-10-16
