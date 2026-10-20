# update the workflow to remove evidence and review artifacts, they are not useful to me rn — Brief

Fill in the two sections marked **Required**: Slice and Outcome. Leave other sections blank if you are unsure. Approval is recorded later, after review. The agent may explain these fields, but you must fill Slice and Outcome yourself.

## Slice — **Required**

**Status:** Approved

**Owner:** Viviana

**Approval:** Viviana, 2026-10-16

**Target cycle:** GGEZ Production Feedback

## Outcome — **Required**

**Goal:** After using ggez for a week, I find myself never using evidence or review file mostly because they are verbose large and difficult to understand and know how to move forward. Our goal is to simplify ggez even further by removing it from part of the process

**Why now:** Documentation drift is a huge issue so reducing the number of maintenance files that we need to use is better imo for simplicity

**User-visible result:** They will no longer see evidence, and review generated once they start a plan. They will also see an updated readme instructions in the public ggez repo, the cli tool doesnt reference it.

**Example:** Sam wants to plan a new feature to include tipping after purchasing a service. He uses ggeez to plan this feature and generates the template files. He starts implementation. Evidence and review are no longer generated and the only artifacts he sees from ggez are brief and task

## Boundaries

**In scope**

- Make `brief.md` and `tasks.md` the complete editable feature file set.
- Stop installing Evidence and Review templates in new projects.
- Remove Evidence and Review requirements from planning handoffs, task instructions, status, managed agent rules, and public documentation.
- Update existing installations safely: remove unchanged managed Evidence and Review templates without deleting third-party feature documents or user edits.
- Keep `ggez status` deterministic when only a Brief and task list exist. Each task has one Result value: `Pending`, `Pass`, `Fail`, `Blocked`, or `Interrupted`.
- Delete existing `evidence.md` and `review.md` feature documents from this repository.
- Add `ggez update` so installed users can download, validate, and atomically activate the latest published ggez release without a source checkout. A failed update must leave the current installation working.

**Out of scope**

- Deleting existing `evidence.md` or `review.md` feature documents from third-party projects.
- Adding a replacement artifact for Evidence or Review.
- Building the planned runner, automatic task conversion, or usage collection.
- Redesigning the Brief or task format beyond what this removal requires.

**Data and systems touched:** CLI initialization, planning, status, installation, and update; user-local ggez releases and launcher; GitHub release archive; install manifests; managed agent instructions; Brief and task templates; this repository's feature documents; README and workflow documentation; automated tests. No credentials are required.

**Prerequisites:** Preserve the current passing test baseline.

## Acceptance checks

- [x] A fresh `ggez init` installs only the Brief and task templates; planning a feature leaves only `brief.md` until an approved task list is added.
- [x] Upgrading an initialized project removes only unchanged managed Evidence and Review templates. Existing feature documents and edited templates are preserved or reported as conflicts.
- [x] This repository no longer contains feature-level `evidence.md` or `review.md` documents; third-party feature documents are never deleted by init or update.
- [x] CLI help, planning handoffs, status output, managed instructions, README, and workflow documentation no longer require or reference Evidence or Review artifacts.
- [x] `ggez status` maps task results exactly: `Fail` to `Check failed`, `Blocked` to `Missing prerequisite`, `Interrupted` to `Run interrupted`, `Pending` to `Ready`, and `Pass` plus a checked task to completed progress. `Running` still requires a live runner signal.
- [x] `ggez status` reports `Complete` only when every task is checked with Result `Pass` and every Brief acceptance check is checked.
- [x] `python3 -B -m unittest discover -s tests -v` passes, including fresh-install, upgrade, plan, and status coverage.
- [x] A local install followed by `ggez init`, `ggez plan`, and `ggez status` completes without creating or requesting Evidence or Review files.
- [x] `ggez update` downloads and validates the latest published release, reports whether it changed the active release, and works without a source checkout. Download, validation, or activation failure leaves the previous launcher and release usable.
- [x] Viviana reviewed the finished workflow and accepted the outcome.

## Safety

**Main risks:** An upgrade could delete a user-edited template, reject a valid older manifest, or leave stale instructions behind. Task Result values and Brief acceptance checks must replace the status signals currently read from Evidence and Review without allowing inconsistent task states. A failed or tampered download must not replace the working CLI launcher.

**Rollback:** Revert the change and reinstall the previous release. Third-party feature documents remain untouched; removed managed templates can be restored by the previous initializer. Repository feature documents deleted by this change can be recovered from Git history.

**Stop the cycle if:** The upgrade cannot distinguish unchanged managed templates from user edits, the CLI cannot reject inconsistent task states, or `ggez update` could replace the working launcher before the new release passes validation.

## Related notes

- Tasks: [Add link when created]
