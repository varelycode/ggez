# CLI installer — Evidence

[Brief](brief.md) · [Tasks](tasks.md)

## TASK-1 — 2026-10-06

**Result:** Pass
**Checks:** 12 tests passed on macOS and Linux; commands and limits below.
**Human review:** Approved

Base: 7a5e051; branch: codex/cli-installer; mode: Verified.
`python3 -B -m unittest discover -s tests -v`: 12 pass on macOS/Python 3.9.6 and Linux/Python 3.12.3 (Playwright Docker image; amd64 emulated).
Git/curl available; temporary write/read passed.

Status reads Brief/Tasks/Evidence/Review. No live signal → never Running; no timing record → unavailable. Completion needs evidence and human acceptance.

Failures: none. Installer checks pending. Viviana approved continuation to TASK-2.

## TASK-2 — 2026-10-06

**Result:** Pass
**Checks:** 32 tests passed on macOS and Linux; commands and limits below.
**Human review:** Approved

Added `scripts/install.sh`, `scripts/install.py`, CLI help, and 20 installer tests. Installations stage bundled files and verify the launcher before activation; failed updates preserve the prior launcher. README has the checkout install command.

`python3 -B -m unittest discover -s tests -v`: 32 pass on macOS/Python 3.9.6 and Linux/Python 3.12.3. `sh -n scripts/install.sh` and `git diff --check` pass.

The first Linux run hit a non-executable temporary mount (6 errors, 1 failure). Added launcher verification and a regression test. All tests pass with an executable mount; a separate noexec smoke test confirms rejection before activation. Linux used the existing Playwright image with amd64 emulation and networking disabled.

Fresh/repeat installs, updates, spaces in paths, missing/old Python, download/permission failures, malformed archives, and preservation checks pass. Tests install into disposable directories; the user's CLI installation was not changed.

Not checked: live GitHub installation; these files are unpublished. Archive download uses a fixture. Viviana approved continuation to TASK-3.

## TASK-3 — 2026-10-06

**Result:** Pass
**Checks:** 53 tests passed on macOS and Linux; commands and limits below.
**Human review:** Approved

Implemented `ggez init [directory]`, `--dry-run`, and `--yes`. Init previews file changes and the instruction diff, installs four templates and a managed AGENTS.md section, and records file hashes. Repeat runs are unchanged; edited or removed managed files, unmarked ggez sections, malformed records, and unsafe paths stop before writing.

Added 21 tests. `python3 -B -m unittest discover -s tests -q`: 53 pass on macOS/Python 3.9.6 and offline Linux/Python 3.12.3 (amd64 container). Includes init from the installed CLI, empty/existing projects, Git/rule/mode preservation, cancellation, interruption, stale previews, template upgrades, and rollback after write failure. `git diff --check` passes. No test failures this task.

Bundled rules cover user-written required fields, Verified/Unverified, approval snapshots, Evidence/Review, and unavailable runner/usage collection. Updated the affected templates and README. Tools remain in scripts/ and tests in tests/.

Limit: compatibility with arbitrary prose in existing project rules needs human review of the preview; `--yes` confirms that review. Hash checks detect managed-file edits, not semantic contradictions. Human review pending; plan/status remain later tasks.

## TASK-4 — 2026-10-06

**Mode:** Unverified, explicitly requested by Viviana.
**Result:** Pass
**Checks:** 11 plan tests passed on macOS and Linux.

Plan creates a title-only Brief, lists local features, and prints the approved handoff prompt. Eleven plan tests pass on macOS and Linux: placeholders, collisions, selection, cancellation, unsafe paths, missing initialization, and failed-write cleanup. Command: `python3 -B -m unittest discover -s tests -p test_plan.py -q`. No failures.

## TASK-5 — 2026-10-06

**Result:** Pass
**Checks:** 83 tests pass on macOS and Linux with `python3 -B -m unittest discover -s tests -q`.

Status reads approval, task checkboxes, latest Result/Checks evidence, and Review acceptance. It reports task counts, stage, state/reason, next action, and available timing. Optional usage records deduplicate attempts and exclude approval waits; no live-run state is inferred. Missing records remain unavailable.

Initial status tests found two failures: empty Goal and Checks fields consumed the next line. Restricted parsing to horizontal whitespace; both regression tests now pass. Added 19 status tests. Status does not write project files.

## TASK-6 — 2026-10-06

**Result:** Pass
**Checks:** 84 tests passed on macOS/Python 3.9.6 and Linux/Python 3.12.3. Command: `python3 -B -m unittest discover -s tests -q`. Linux used the existing Playwright amd64 image, an executable temporary mount, and disabled networking. The final timing guard also passed the 19-test status suite on macOS.

Added an installed-CLI walkthrough for fresh and existing projects: install → init → plan → status → recorded task evidence → Review → sample human acceptance. It confirms that Brief placeholders and existing project files survive and repeat init makes no changes. Sample acceptance exists only in disposable test directories.

README is 982 characters; workflow is 567. `sh -n scripts/install.sh` and `git diff --check` pass. Full Brief, Tasks, and Evidence exceed the general 600-character cap to preserve the complete feature records requested in this repository. No other new Markdown outside the exempt templates exceeds the cap.

During documentation verification, a 1,026-character README draft failed the length check before being saved; shortened it to 982. No product-test failures in this task.

### Claim checks

| Brief check | Evidence | Result |
| --- | --- | --- |
| macOS/Linux install; offline commands | Installer suite and offline Linux walkthrough | Pass |
| Preserve Git and existing setup | Init preservation tests | Pass |
| One-line install/init/plan/status instructions | README and installed workflow test | Pass for checkout; public URL awaits publication |
| Init preview, repeat runs, conflicts | 21 init tests | Pass |
| Workflow, evidence, layout, tracking limits | Bundled rules and installed-init test | Pass |
| Blank Brief; user-written required fields | Plan placeholder and handoff tests | Pass |
| Feature picker and cancellation | Plan and status selection tests | Pass |
| Verified/Unverified instructions | Prompt, templates, and status review-gate tests | Pass |
| Markdown limits | Character checks | Full feature records retained as requested |
| Goal, task progress, recorded time | 19 status tests | Pass |
| State, checks, and human acceptance | Status state tests and installed walkthrough | Pass; no runner signal is fabricated |
| Failure recovery and clear next steps | Installer/init/plan/status error tests | Pass |
| Required automated checks | Full suite, 84 tests | Pass |
| Fresh/existing local walkthrough | test_workflow.py on macOS/Linux | Pass |

### Remaining limits

The public GitHub download is not live-tested: the installer is unpublished. Local installation and archive download fixtures pass. Arbitrary prose conflicts still require review of the init preview. No runner or automatic time/token collection is included. Final human acceptance is pending in Review; nothing was merged or published.

## TASK-5 follow-up — simplify status output

Requested by Viviana: omit Goal, State, and Next from printed status. Kept feature, current task, stage, completion, recorded time, and full file paths. Updated the Brief, task contract, CLI help, and README.

The output regression test failed before the change, then passed. All 84 tests pass on macOS and Linux; state/approval logic remains tested internally. README: 995 characters. `git diff --check` passes.

## Post-merge check — 2026-10-06

PR #1 merged as bb3c528. The unauthenticated README install URL returns 404 because the repository is private, confirmed with `gh repo view --json visibility`. No visibility changes made. Local-checkout installation remains the verified route.

## Public installer recheck — 2026-10-06

After Viviana made the repository public, the README URL downloaded successfully. Installation, help, init, plan, and status all passed in a disposable directory using the public downloads. The earlier private-repository limitation is resolved; temporary files were removed.
