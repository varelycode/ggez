# Brief and task revision lineage — Tasks

**Revision:** tasks-01a1d5d5-f9af-7fba-a27d-5fab4837cb63-86abb149e50910e7

**Content digest:** sha256:86abb149e50910e738b48a115e0d5b679c3822a6ef1cfbc35a101e7575b02766

**Derived from:** brief-01a1d5cf-1320-784f-bdb0-aa73cadbbe9b-3cea004b48b88494

> Edit this document as the task source. Keep TASK-N IDs stable when renaming or reordering tasks; never reuse IDs. Approve this document before execution. Later edits become a new draft and need fresh approval before use.

**Brief:** [brief.md](brief.md)

**Approval:** Viviana, 2026-11-13

**Mode:** Unverified

## Queue

- [x] TASK-1 — Verify revision boundaries and project prerequisites

  - **Result:** Pass
  - Done when: The current Brief, task, status, template, selector, and test behavior has been checked against the approved scope; the canonical definition fields and mutable state fields are recorded in the active agent run before implementation.
  - Verify: prerequisites: `python3 --version` reports Python 3.9 or newer; `python3 -B -m unittest discover -s tests -v` passes before feature changes.
  - Must not: alter source files; include approval, status, task Results, task checkboxes, acceptance checkboxes, or generated revision metadata in canonical definition digests.

  <details>
  <summary>Implementation details</summary>

  Read the approved Brief and its direct Context sources. Confirm how `ggez plan`, document parsing, feature selection, `ggez status`, installed templates, and current tests behave. Record which Brief and task fields define content and which fields are mutable workflow state. Confirm that UUIDv7 generation and fuzzy matching can support Python 3.9 without adding a dependency.

  Category: setup
  Complexity: low

  - [x] 1. Inspect the approved sources: Read the Brief and every direct Context path, then report any contradiction before editing.
  - [x] 2. Define canonical content boundaries: Include requirement and instruction text; exclude revision metadata and mutable approval, Result, and checkbox state.
  - [x] 3. Verify prerequisites: Run the Python version check and complete test suite, preserving the real results.

  </details>

- [x] TASK-2 — Implement immutable revision identities

  - **Result:** Pass
  - Done when: ggez can create, parse, verify, and decode Brief and task-set revision identities that combine UUIDv7 time and uniqueness with a SHA-256 content digest; unchanged canonical content reuses its identity.
  - Verify: revision identity tests: focused unit tests cover deterministic injected time/randomness, digest verification, time decoding, malformed IDs, same-content reuse, and collision handling; the full suite passes.
  - Must not: use timestamps alone as identity; depend on Python features newer than 3.9; hash a revision ID or mutable workflow state into its own content digest.
  - Depends on: TASK-1

  <details>
  <summary>Implementation details</summary>

  Add revision primitives in the existing Python style. Use a UUIDv7 component for sortable creation time and random uniqueness. Include a readable digest suffix in the revision ID and retain enough SHA-256 data to verify canonical document content. Parse IDs strictly and expose the embedded creation time for display. Treat the same ID and digest as the same revision; reject the same ID with different content.

  Category: functional
  Complexity: medium

  - [x] 1. Canonicalize definitions: Normalize only the agreed structural fields while preserving meaningful text and ordering.
  - [x] 2. Generate and parse identities: Support Brief and task-set namespaces, UUIDv7 creation time, uniqueness, and digest verification.
  - [x] 3. Verify revision primitives: Add focused unit tests and run the full suite.

  </details>

- [x] TASK-3 — Add the revision lifecycle to Briefs and task sets

  - **Result:** Pass
  - Done when: `ggez revise brief [feature]` stamps or reuses the current Brief revision, and `ggez revise tasks [feature]` stamps or reuses the task-set revision while recording the exact current Brief revision as its source; omitting `[feature]` selects the only feature or opens a cancellable fuzzy selector.
  - Verify: lifecycle and selection tests: tests cover first stamping, idempotent reuse, substantive Brief and task changes, state-only changes, atomic writes, missing approval, missing tasks, exact feature arguments, one-feature auto-selection, fuzzy selection, cancellation, no matches, and a task set derived from an older Brief.
  - Must not: approve documents on the user's behalf; rewrite task definitions; update a stale task set to a new Brief revision without regenerating and approving its content; reconstruct unrecorded provenance; require `fzf` or another external executable.
  - Depends on: TASK-2

  <details>
  <summary>Implementation details</summary>

  Add revision placeholders to the Brief and task templates without pre-filling required user content. Add a focused `ggez revise` CLI action that writes only managed revision metadata and preserves the rest of each document. An explicit feature slug selects directly. With no slug, reuse a shared selector that chooses the sole feature automatically and accepts a number or fuzzy text when several features exist; Enter cancels. Brief revisions may be stamped only from valid feature documents. Task revisions require an approved, digest-valid Brief and store `Derived from` using its exact revision ID. A changed Brief leaves existing tasks untouched and therefore stale. Existing documents without metadata can be stamped as a new current revision, but old lineage must remain unknown.

  Category: functional
  Complexity: high

  - [x] 1. Extend document formats: Add revision, digest, and task-source fields with clear placeholder behavior.
  - [x] 2. Add fuzzy feature selection: Extend the shared selector without a runtime dependency; preserve exact selection, one-feature behavior, and cancellation.
  - [x] 3. Implement safe stamping: Validate before writing, use atomic replacement, and make unchanged content idempotent.
  - [x] 4. Preserve workflow state: Keep approval, acceptance, Results, completion checkboxes, and task status outside definition identity.
  - [x] 5. Verify lifecycle behavior: Add focused CLI, selector, and file-preservation tests, then run the full suite.

  </details>

- [x] TASK-4 — Validate and report revision lineage

  - **Result:** Pass
  - Done when: `ggez check [feature]` validates revision metadata and lineage without writing, while `ggez status [feature]` displays Brief and task-set revisions, decoded creation times, and an actionable stale or missing-metadata state.
  - Verify: validation and status tests: tests cover matching lineage, a revised Brief with old tasks, changed content under an old ID, duplicate ID conflicts, malformed IDs, identical content regenerated under another ID, and legacy documents without metadata.
  - Must not: silently repair documents; classify stale tasks as current; add new status states or Needs attention reasons; compare a preserved run snapshot with a newer editable draft as a synchronization error.
  - Depends on: TASK-3

  <details>
  <summary>Implementation details</summary>

  Add the planned read-only `ggez check` command and reuse its validation from status. Give `check` the same optional feature argument and shared selector behavior as `revise` and `status`. Report stale or missing lineage as `Needs attention` with the existing `Missing prerequisite` reason. Show revision creation times decoded from UUIDv7 rather than stored separately. Reject the same revision ID with conflicting content. Treat different IDs with the same digest as identical regenerated content and provide an actionable reuse warning. Legacy documents remain readable and receive instructions for creating a new known revision; ggez must not claim their prior provenance.

  Category: functional
  Complexity: high

  - [x] 1. Validate exact lineage: Verify IDs, full digests, source Brief IDs, duplicates, and canonical content.
  - [x] 2. Add read-only reporting: Implement `ggez check` and extend status without changing files or existing state vocabulary.
  - [x] 3. Verify failures and recovery: Add focused tests for every acceptance and legacy case, then run the full suite.

  </details>

- [x] TASK-5 — Update installed guidance and prove the complete workflow

  - **Result:** Pass
  - Done when: Templates, installed agent rules, CLI handoff text, help, README, and workflow documentation describe one revision lifecycle that agrees with implemented behavior; a local walkthrough proves stale-task detection and regeneration recovery.
  - Verify: complete feature: `python3 -B -m unittest discover -s tests -v` passes; Markdown limits and `git diff --check` pass; the walkthrough selects a feature by fuzzy text, creates and stamps a Brief and tasks, displays creation times, revises the Brief, reports stale tasks, and stamps a regenerated task set that matches.
  - Must not: claim automatic task generation, Ralph execution, run snapshots, or usage collection; duplicate the full workflow across documents when a short command reference is enough; mark Brief acceptance checks for the user.
  - Depends on: TASK-4

  <details>
  <summary>Implementation details</summary>

  Update the source templates and managed `AGENTS.md` block so `ggez init` can preview and install the new lifecycle without overwriting local instructions. Keep current and planned behavior separate. Update concise public documentation and CLI help. Exercise a temporary sample project through the exact commands in the acceptance checks, including a legacy feature and a regenerated task set. Report the commands and observed results in the active agent run.

  Category: integration
  Complexity: medium

  - [x] 1. Align managed guidance: Update templates, agent rules, handoff text, help, and concise documentation from one agreed lifecycle.
  - [x] 2. Verify installation compatibility: Cover fresh init, managed updates, local instruction conflicts, and legacy feature documents.
  - [x] 3. Run the complete checks: Execute the full suite, Markdown and diff checks, and the local stale-to-current walkthrough.

  </details>

- [x] TASK-6 — Refactor ggez.py for readability

  - **Result:** Pass
  - Done when: `scripts/ggez.py` keeps the same behavior while its responsibilities are grouped in a clear reading order, revision and lineage records use named structures instead of opaque dictionaries, repeated logic is reduced, and small cohesive components follow the applicable SOLID principles.
  - Verify: behavior-preserving refactor: `python3 -B -m unittest discover -s tests -v`, `python3 -B -m py_compile scripts/ggez.py`, `git diff --check`, `ggez check brief-and-task-revision-lineage`, and the installed CLI workflow all pass without changing command output or document formats.
  - Must not: change revision semantics, CLI arguments, output fields, templates, status transitions, installation behavior, or the single-file installed entry point.
  - Depends on: TASK-5

  <details>
  <summary>Implementation details</summary>

  Reorder helpers into labeled sections that follow the workflow from shared primitives through initialization, feature selection, planning, revisions, status, installation, and CLI dispatch. Separate revision encoding, document persistence, lineage validation, and CLI presentation. Introduce small named records for parsed revisions, document revision state, and lineage state. Inject clock, entropy, and replace operations at the narrow boundaries that need deterministic tests. Favor composition and focused functions; do not add inheritance or abstractions without a second concrete use.

  Category: refactor
  Complexity: medium

  - [x] 1. Establish a readable file structure: Group related constants, records, and functions in workflow order without changing behavior.
  - [x] 2. Separate responsibilities: Isolate revision encoding, persistence, validation, and presentation behind narrow boundaries.
  - [x] 3. Replace opaque records: Use named immutable structures for revision and lineage data, then simplify their callers.
  - [x] 4. Remove local repetition: Consolidate feature resolution and revision display logic while preserving exact output.
  - [x] 5. Prove behavior is unchanged: Run focused revision/status tests, the full suite, compilation, install checks, and lineage validation.

  </details>

## Ralph rules

1. Verified is the default: complete one approved task, test it, set Result to `Pass`, check it, then wait for human review. Explicit Unverified mode continues approved tasks after tests; stop conditions and final human acceptance remain required.
2. Stay within task scope and honor the Brief's stop conditions.
3. Use exactly one Result per task: `Pending`, `Pass`, `Fail`, `Blocked`, or `Interrupted`. Check a task exactly when its Result is `Pass`.
4. Report checks, failures, and corrections in the active agent run. Keep secrets and private data out.
5. Stop on scope expansion or repeated failure and set the current task Result before handing off.

## Status

**Next task:** Outcome review
