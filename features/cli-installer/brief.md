# Simple CLI installer — Brief

Fill in the two sections marked **Required**: Slice and Outcome. Leave other sections blank if you are unsure. Approval is recorded later, after review. Ask for help whenever you need it.
## Slice — **Required**

**Status:** Approved
**Owner:** Viviana

**Approval:** Viviana, 2026-10-06 (Brief only; tasks require separate approval).

**Target cycle:** CLI Tool feature

## Outcome — **Required**

**Goal:** Make it easy for people to manage the ggez loop framework

**Why now:** I want to share the tool with others to use and I do not wanna have to verbally explain how to use this loop.

**User-visible result:**
- Be able to install the CLI using an install script with a one-line instruction in the README.md
- Be able to init the framework in their own existing or new project using the CLI tool, with a one-line instruction in the readme

**Example:**
Scenario 1: Ana is frustrated by not being able to clearly read spec documents written by Claude or Codex, she wants to try a new tool that will help her figure out how to interact better when developing features
Scenario 2: Jose wants to do an overnight run of a feature his product team is pushing him to do this week. He wants to run a feature spec overnight while he’s sleeping and review it in the morning. However, past runs have made it difficult to trust that the agent will do the right thing. So he wants to have clearly outlined tasks he can review if they’re done in the morning and evidence of how the features were tested.
## Boundaries

**In scope**

- init
- install script to use CLI
- status update of the run with basic goal read out and status update, and percentage of tasks completed, and time ran
- `ggez plan "Feature title"` creates a blank Brief with that title and prints a short loop overview and a copyable agent prompt. The user must fill Slice and Outcome; the agent never fills those required fields.
- Templates explain Verified (default) and Unverified execution. Both require approved tasks, tests, and evidence.
- one-line readme instructions for init, status, plan

**Out of scope**

- skill companion
- cli pausing or updating a feature

**Data and systems touched:** The ggez repository and README; a user-owned CLI installation directory; the target project’s AGENTS.md, .ggez/templates/, and features/ documents; local run records if available. GitHub supplies the installer. No model API credentials or access to private notes is needed.

**Prerequisites:** Ready: Python 3.9.6, Git, the existing templates, and all 12 current tests pass with `python3 -B -m unittest discover -s tests -v`. Still to verify: installer download tools, clean-install behavior, PATH setup, and supported-platform checks. A runner and automatic usage collection do not exist yet; reliable live status and timing need an agreed data source.

## Acceptance checks

- [ ] Installation supports macOS and Linux with Python 3.9+ and a user-local install script. Windows support is out of scope. Init, plan, and status work offline after installation.
- [ ] Init preserves the project’s Git history and setup; it creates neither an app nor a Git repository.
- [ ] The README provides one tested install command and one example each for init, plan, and status. Installation makes `ggez --help` available, or gives the exact PATH step required.
- [ ] `ggez init` works in both an empty directory and an existing project. It previews changes, copies templates, and adds the ggez workflow rules without replacing unrelated agent instructions. Repeating it creates no duplicates; edited files and conflicting rules require resolution.
- [ ] Installed rules explain approval, feature-level Evidence and Review, document/run layout, and the limits of usage tracking. They never claim an unavailable runner or tracker is active.
- [ ] `ggez plan "Feature title"` creates a blank Brief in a unique feature folder. It preserves existing files, rejects unsafe paths, and prints a copyable agent prompt. Slice and Outcome stay blank for the user. The agent may explain required fields and suggest optional sections when asked, but never fills required fields.
- [ ] `ggez plan` without a title lists features in the current project and “New feature.” Selecting a feature shows its Brief path and next-step prompt without editing it. An empty list offers creation; cancelling writes nothing.
- [ ] Verified is the default. Templates and the handoff prompt explain both modes; the receiving agent executes tasks, and the CLI does not launch or supervise a runner. Verified mode runs one approved task, tests it, records evidence, and waits for human review. Explicitly requested Unverified mode continues through approved tasks without per-task review; tests and evidence remain required. Both stop on failures or blockers; final acceptance stays human.
- [ ] Repository Markdown stays under 600 characters, except AGENTS.md and templates; README stays under 1,000. Instructions and prompts explain the next action briefly.
- [ ] `ggez status` selects the only feature automatically or offers a choice when several exist. It reads available local task/evidence records and shows the selected feature, goal, stage, current task, state/reason, completed/total tasks, percentage, and recorded execution time. No tasks means “Not available,” not division by zero. Missing or partial timing is labeled; approval waits are excluded when timing is recorded.
- [ ] Status uses Ready, Running, Needs attention, or Complete. Running requires a live runner signal; Complete requires checks and human acceptance. Task checkboxes alone do not prove either state.
- [ ] Failed installation, missing prerequisites, uninitialized projects, malformed records, and multiple features produce clear next steps. Failures preserve existing files and leave no partial installation presented as successful.
- [ ] Automated tests cover installation, repeat initialization, preservation/conflicts, plan creation, and status calculations and missing data. Run `python3 -B -m unittest discover -s tests -v`; add exact installer smoke-test commands with implementation.
- [ ] Walk through install → init → plan → status in disposable fresh and existing projects. Review the generated agent prompt and verify that a draft Brief remains unapproved.

## Safety

**Main risks:** Overwriting project instructions or edited templates; writing outside the selected project; a failed update breaking the CLI; verbose edits or violating AGENTS.md character limits, and reporting unverified progress or invented run time; creating extra documentation; documentation drift; documentation bloat; feature regression; Preview mutations, validate paths, preserve user edits, and label missing evidence;

**Rollback:** Remove only the CLI installation and ggez-managed files/sections created by this installation, after inspecting the recorded changes. Preserve feature documents and user edits. Restore modified files from their pre-change backup or Git diff. Installation must not require administrator access or modify shell configuration silently.

**Stop the cycle if:** Existing instructions or user edits conflict with installation; reliable status requires adding a runner or model integration; a supported platform cannot be tested; or the proposed scope exceeds the approved Brief.

## Related notes

- Tasks: [Review task list](tasks.md) — awaiting approval.
- Evidence: Not created; one file for this feature.
- Review: Not created; acceptance remains Viviana’s decision.
