# Require context for every Brief — Brief

Fill in the two sections marked **Required**: Slice and Outcome. Leave other sections blank if you are unsure. Approval is recorded later, after review. The agent may explain these fields, but you must fill Slice and Outcome yourself.

## Slice — **Required**

**Status:** Approved

**Owner:** Viviana

**Approval:** Viviana, 2026-10-20

**Target cycle:** Tool improvement

## Outcome — **Required**

**Goal:** Require each Brief to name the context an agent must read before preparing tasks. This should preserve continuity across features without loading the whole project.

**Why now:** We want to use ggez from a parent folder that contains two repositories and a large documentation set. The agent needs a small, explicit context set so it can find relevant history without loading noise.

**User-visible result:** After updating ggez, every new Brief includes a required Context section. The user lists up to five direct sources with a reason for each, or states that no additional context is needed.

**Example:** Viviana starts a feature in an Aramco parent folder that contains two repositories. She adds the main epic and the previous feature Brief to Context. The agent reads those sources before preparing tasks, while unrelated documentation stays out of the working context.

## Context — **Required**

Read these sources before preparing tasks. Do not load references found inside them unless the work requires it.

- [Agent rules](../../AGENTS.md) — approval, testing, documentation, and init requirements.
- [Brief template](../../templates/prd.md) — current Brief structure and required fields.
- [CLI implementation](../../scripts/ggez.py) — plan handoff and status approval logic.
- [Plan tests](../../tests/test_plan.py) and [status tests](../../tests/test_status.py) — current observable behavior.

**ggez architecture**

- One Python entry point provides `init`, `plan`, `status`, and `update`.
- `init` manages `.ggez/templates/`, `.ggez/install.json`, and the marked ggez section in `AGENTS.md`.
- `brief.md` and `tasks.md` are the editable source of truth. `status` reads them; the CLI does not run agents.
- At a parent root, ggez keeps shared workflow files there. Each child repository keeps its own Git history and instructions.

## Boundaries

**In scope**

- Add one required Context section to the Brief template.
- Accept one to five direct paths or URLs with a reason for each, or the exact statement `None beyond AGENTS.md and this Brief`.
- Tell the planning agent to read the listed context before preparing tasks. Do not follow nested references automatically.
- Keep invalid Context at `Brief / Approval required`, and update managed instructions, concise documentation, and tests.

**Out of scope**

- Context IDs, per-task packs, indexes, freshness metadata, relevance checks, or automatic discovery.
- A separate context file, new command, or recursive reference loading.
- Masking, summarization, retrieval infrastructure, runner changes, or model-managed live context.
- Migrating or rewriting existing feature Briefs.

**Data and systems touched:** Brief and task templates, planning handoff, status validation, managed agent instructions, README, workflow documentation, and automated tests. Existing feature documents and child Git repositories must remain unchanged.

**Prerequisites:** The user must complete Slice and Outcome and approve this Brief. The current Python test suite remains the baseline. Relevant init and workflow tests passed on 2026-10-20.

## Acceptance checks

**Behavior**

- [ ] A newly planned Brief contains one required Context section with room for up to five direct references and a reason for each.
- [ ] `None beyond AGENTS.md and this Brief` satisfies the requirement without forcing an unnecessary reference.
- [ ] A placeholder, empty section, more than five references, or a reference without a reason keeps status at `Brief / Approval required`.
- [ ] The planning handoff tells the agent to read the Context entries before preparing tasks and does not require recursive loading.

**Verification**

- [ ] Existing Briefs are not migrated or rewritten. Re-running init preserves user edits and updates only unchanged managed files.
- [ ] `python3 -B -m unittest discover -s tests -v` passes.
- [ ] A local install can initialize an untracked parent folder containing two child repositories, create a Brief with Context, and leave both child repositories unchanged.
- [ ] Viviana reviews the installed workflow and accepts the outcome.

## Safety

**Main risks:** The Context section could imply that listed sources are complete, encourage oversized references, or block older Briefs unexpectedly. Init could overwrite an edited template or managed instruction block. A parent `AGENTS.md` may affect agents working inside both child repositories, so existing child instructions must still be respected.

**Rollback:** Revert the template, handoff, validation, instructions, documentation, and tests, then reinstall the previous release. Existing Briefs and child repositories require no data migration and remain recoverable from their current storage or Git history.

**Stop the cycle if:** The change requires a new context artifact, runner integration, semantic relevance checking, automatic retrieval, or rewriting existing Briefs; init cannot preserve user edits; or parent-root installation changes a child repository.

## Related notes

**Tasks:** [Task list](tasks.md)

- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)
- [Chroma: Context Rot](https://www.trychroma.com/research/context-rot) — reports nonuniform degradation as context grows; it does not establish a universal exponential curve.
- [JetBrains study: The Complexity Trap](https://arxiv.org/abs/2508.21433) — observation masking reduced cost on software tasks without a consistent significant solve-rate gain.
- [Context Language Models](https://arxiv.org/abs/2609.37725) — early work on model-managed live context; runner support is outside this slice.
- [Nielsen Norman Group: Context Libraries](https://www.nngroup.com/articles/context-libraries/) — qualitative evidence that context libraries drift, become hard to find, and need local scoping.

**Excluded claim:** The quoted 65% enterprise-failure figure is not included because its dataset and methodology could not be traced.
