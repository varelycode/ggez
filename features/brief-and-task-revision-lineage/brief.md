# Brief and task revision lineage — Brief

**Revision:** brief-01a1d5cf-1320-784f-bdb0-aa73cadbbe9b-3cea004b48b88494

**Content digest:** sha256:3cea004b48b88494b58a603427b56a8d60f2f2046f9d0664f5b1a940fead37bf

Fill in the two sections marked **Required**: Slice and Outcome. Leave other sections blank if you are unsure. Approval is recorded later, after review. The agent may explain these fields, but you must fill Slice and Outcome yourself.

## Slice — **Required**

**Status:** Approved

**Owner:** Viviana

**Approval:** Viviana, 2026-11-13

**Target cycle:** Fix documentation drift

## Outcome — **Required**

**Goal:** They will be able to tell if tasks are stale after making a revision to the brief, the ggez framework can tell which tasks match to with brief revision

**Why now:** I need the flexibility to make changes to approve drafts because sometimes shit changes and need to be able to tell how those changes were made when i am confused

**User-visible result:** Each brief has a unique id representing the time and the uniqueness and each task is associated with the unique id from which brief it was generated from

**Example:** Viviana approves Brief revision `brief-019a7f3c-7f3ac198b620`, and ggez generates a task set derived from that ID. She later revises the Brief, which receives a new ID. `ggez check` reports that the existing tasks belong to the earlier revision and are stale until a new task set is generated; ggez can also display when either revision was created from its ID.

## Context — **Required**

<!-- List 1–5 direct paths or URLs with a reason for each. Do not list references found inside them. If no additional context is needed, replace the placeholder with exactly: None beyond AGENTS.md and this Brief -->

- `scripts/ggez.py` — Current feature creation, document parsing, digest, status, and CLI behavior.
- `templates/prd.md` — Source format for new Briefs.
- `templates/tasks.md` — Source format and lifecycle rules for generated task sets.
- `tests/test_status.py` — Existing validation and status behavior that revision checks must preserve.

## Boundaries

**In scope**

- Give each approved Brief revision and task-set revision an immutable UUIDv7-based ID with a verifiable content digest.
- Record the exact source Brief revision on its generated task set.
- Decode and display revision creation time when useful.
- Detect changed, duplicated, missing, or stale revision metadata without silently rewriting approved files.
- Preserve task revision identity when only task Results or completion checkboxes change.
- Give existing feature documents without revision metadata an actionable, non-destructive upgrade path.
- When a revision command omits the feature, let the person select from existing features using dependency-free fuzzy matching.

**Out of scope**

- Automatic semantic merging or bidirectional synchronization between Briefs and tasks.
- Deciding whether a task set adequately implements the Brief beyond exact revision lineage.
- Ralph run snapshots, runner integration, and usage tracking.
- Reconstructing provenance that was never recorded for an existing feature.
- Requiring `fzf` or another external selector.

**Data and systems touched:** Feature `brief.md` and `tasks.md` files, document templates, ggez CLI validation and status output, and unit tests.

**Prerequisites:** None.

## Acceptance checks

- [x] An approved Brief revision has an immutable revision ID containing time and uniqueness, plus a digest that verifies its canonical definition; its task set has its own revision ID and names that exact Brief revision as its source.
- [x] Changing Brief requirements makes existing tasks stale; changing task instructions creates a new task-set revision; approval, acceptance, Result, and completion-state updates do not change definition revisions.
- [x] ggez reports conflicting duplicate IDs, changed content, stale task lineage, and missing legacy metadata with an actionable message and without overwriting documents.
- [x] With no feature argument, a revision command selects the only feature automatically or offers a cancellable fuzzy selector when several features exist; an explicit feature remains supported.
- [x] `python3 -B -m unittest discover -s tests -v` passes with coverage for matching, stale, duplicate, state-only, and legacy document cases.
- [x] A local walkthrough creates a Brief revision and task set, displays their creation times, revises the Brief, and shows that the earlier tasks are stale until a new task set is generated.

## Safety

**Main risks:** Hashing revision metadata into itself, treating execution-state edits as definition changes, accepting the same ID with different content, invalidating existing approvals, or breaking legacy features that have no IDs.

**Rollback:** Revert the CLI, template, and instruction changes. Preserve all revision fields already written as inert Markdown; do not rewrite or delete feature history.

**Stop the cycle if:** The implementation would rewrite approved history, require automatic task generation, Ralph integration, or an external fuzzy-finder dependency, or cannot define canonical Brief and task content without mixing in mutable execution state.

## Related notes

- Tasks: [tasks.md](tasks.md)
