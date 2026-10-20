# Require context for every Brief — Tasks

> Edit this document as the task source. Keep TASK-N IDs stable when renaming or reordering tasks; never reuse IDs. Approve this document before execution. Later edits need fresh approval.

**Next action:** Review and approve this file. Choose Unverified if you want all three tasks to run without per-task review pauses.

**Brief:** [Require context for every Brief](brief.md)

**Approval:** Viviana, 2026-10-20

**Mode:** Unverified

## Queue

- [x] TASK-1 — Verify project prerequisites and baseline

  - **Result:** Pass
  - **Estimate:** 5 minutes if the baseline passes.
  - Done when: The approved Brief, affected files, repository state, and current test baseline are verified; any blocker is reported before implementation.
  - Verify: baseline: `python3 -B -m unittest discover -s tests -v` passes.
  - Must not: change implementation files; expose secrets or unrelated private content.

  <details>
  <summary>Implementation details</summary>

  Read the Brief and its Context section. Inspect the Brief template, planning handoff, status parser, managed rules, documentation limits, and focused tests. Confirm that the existing initializer preserves unrelated files and Git repositories.

  Category: setup
  Complexity: low

  - [x] 1. Read the approved Brief and direct Context references.
  - [x] 2. Run the full baseline test suite and report any failure before changing code.

  </details>

- [x] TASK-2 — Require Context before task preparation

  - **Result:** Pass
  - **Estimate:** 25 minutes with the existing test structure.
  - Done when: New Briefs contain the required Context section; one to five direct references with reasons or the exact no-extra-context statement are accepted; missing, placeholder, malformed, or oversized Context keeps the feature at Brief approval.
  - Verify: planning and status: focused plan and status tests cover valid references, the no-extra-context statement, placeholders, missing reasons, and more than five references.
  - Must not: add a context file, command, index, task pack, automatic discovery, recursive loading, summarization, retrieval, or runner behavior; rewrite existing Briefs.
  - Depends on: TASK-1

  <details>
  <summary>Implementation details</summary>

  Add `## Context — **Required**` to the Brief template after Outcome. Its instructions allow one to five direct paths or URLs, each followed by a reason, or `None beyond AGENTS.md and this Brief`. Update the plan handoff to require reading those entries before tasks. Add deterministic Context validation to status without fetching sources or judging relevance.

  Category: functional
  Complexity: medium

  - [x] 1. Update the Brief template and planning handoff.
  - [x] 2. Add Context parsing and the Brief-stage approval gate.
  - [x] 3. Add focused plan and status tests for accepted and rejected forms.
  - [x] 4. Run the focused tests.

  </details>

- [x] TASK-3 — Install and document the Context workflow

  - **Result:** Pass
  - **Estimate:** 15 minutes if the install walkthrough passes.
  - Done when: Managed instructions and concise public documentation describe the Context requirement; init upgrades unchanged managed files safely; an untracked parent with two child repositories can use the workflow without changing either child repository.
  - Verify: complete workflow: `python3 -B -m unittest discover -s tests -v` passes, followed by a disposable install → parent init → plan → status walkthrough with two nested Git repositories.
  - Must not: modify child repository files or Git history; overwrite edited managed files; claim that ggez runs agents or performs automatic context management.
  - Depends on: TASK-2

  <details>
  <summary>Implementation details</summary>

  Update the managed ggez rules, README, and workflow documentation within their size limits. Cover fresh init and safe upgrade behavior. Test the installed CLI from an untracked parent containing two nested repositories and confirm that the child repositories remain unchanged.

  Category: integration
  Complexity: medium

  - [x] 1. Update managed rules and concise documentation.
  - [x] 2. Add or adjust init and workflow coverage.
  - [x] 3. Run the full test suite and disposable two-repository walkthrough.

  </details>

## Ralph rules

1. Verified is the default: complete one approved task, test it, set Result to `Pass`, check it, then wait for human review. Explicit Unverified mode continues approved tasks after tests; stop conditions and final human acceptance remain required.
2. Stay within scope and honor the Brief’s stop conditions.
3. Use exactly one Result per task: `Pending`, `Pass`, `Fail`, `Blocked`, or `Interrupted`. Check a task exactly when its Result is `Pass`.
4. Report checks, failures, and corrections in the active agent run. Keep secrets and private data out.
5. Stop on scope expansion or repeated failure and set the current task Result before handing off.

## Status

**Next task:** None — ready for outcome review
