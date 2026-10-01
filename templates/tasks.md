# {{Feature name}} — Tasks

> Edit this document as the task source. Keep TASK-N IDs stable when renaming or reordering tasks; never reuse IDs. Hidden Ralph JSON will be generated from the approved document. The converter is not implemented yet.

**Brief:** {{Brief link}}

**Evidence:** {{Evidence link}}

## Queue

- [ ] TASK-1 — Verify project prerequisites and access

  - Done when: {{Required tools, access, and test data are verified, with any blocker recorded in Evidence}}; No secrets or private note contents appear in committed artifacts.
  - Verify: prerequisites: {{List exact safe checks and their expected results; record unavailable access without exposing secret values}}
  - Must not: start feature work while a required prerequisite is blocked.; copy secret values into task files, logs, or evidence.

  <details>
  <summary>Implementation details</summary>

  Check the agreed Brief and the prerequisites needed to build and verify this slice.

  Category: setup
  Complexity: low

  - [ ] 1. Read the Brief and identify required setup: Read .agent/prd/PRD.md. Use its Prerequisites field; record only relevant tools, services, environment variable names, and test data.
  - [ ] 2. Verify: prerequisites: {{List exact safe checks and their expected results; record unavailable access without exposing secret values}}

  </details>

- [ ] TASK-2 — {{One bounded feature outcome}}

  - Done when: {{Observable success result}}; {{Relevant failure or recovery result}}
  - Verify: behavior and recovery: {{Exact focused checks and expected results, including native Mac checks where relevant}}
  - Must not: {{Specific excluded behavior from the Brief}}
  - Depends on: TASK-1

  <details>
  <summary>Implementation details</summary>

  {{Expected behavior and the specific Brief acceptance checks covered}}

  Category: functional
  Complexity: low

  - [ ] 1. {{Implement the bounded change}}: {{Verified files, interfaces, and implementation guidance}}
  - [ ] 2. Verify: behavior and recovery: {{Exact focused checks and expected results, including native Mac checks where relevant}}

  </details>

## Ralph rules

1. Read the Brief. Work on the first unchecked task only; stop if blocked.
2. Stay within its scope and honor the Brief’s stop conditions.
3. Record checks, failures, corrections, and results in Evidence. Keep secrets and private data out.
4. Record verified completion against the executed task ID and revision. Checkboxes alone do not prove completion; preserve this editable source.
5. Stop on scope expansion or repeated failure; record the blocker in Evidence.

## Status

**Next task:** TASK-1 — Verify project prerequisites and access

**Blocked by:** [Known blocker, or Not checked]
