# [Feature name] — Evidence

**Brief:** [Link]

**Tasks:** [Link]

## Run record

**Started:** [Date and time]

**Starting revision:** [Commit]

**Starting branch:** [Branch]

**Target branch:** [Branch]

**Mode:** [Verified / Unverified]

## Claim checks

Add a row for each Brief acceptance check. Use Pending, Pass, Fail, or Not applicable with a reason. Automated checks do not imply human approval.

| Claim | Mechanical evidence | Human check | Status |
| --- | --- | --- | --- |
| [Acceptance check] | [Command result or artifact link] | Pending | Pending |

## Commands and results

Record each task attempt as it happens, including failures and corrections. Repeat this block for each task.

### [TASK-N] — [Date]

**Result:** [Pass / Fail / Blocked / Interrupted]

**Human review:** [Pending / Approved; only record approval when the user gives it]

**Revision checked:** [Commit, plus any uncommitted changes]

**Changed:** [Behavior and files]

**Checks:** [Exact commands, results, and links to logs or screenshots]

**Failures and corrections:** [What failed, what changed, and rerun results; or None]

**Not checked / blocked:** [Missing checks, blockers, and remaining uncertainty; or None]

## Data provenance

[If external or live data was used: source, retrieval time, permissions, and relevant counts. Otherwise, write Not applicable. Keep credentials, private note content, and account identifiers out of evidence.]

## Diff review

- [ ] Changed files match the approved task.
- [ ] Tests were not weakened to pass.
- [ ] No credentials or private content appear in code, logs, screenshots, or notes.
- [ ] Remaining uncertainty is recorded.
