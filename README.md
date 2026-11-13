# ggez

ggez keeps feature work in a Brief and task plan with immutable revision lineage.

1. Fill the Brief, record its revision, and get approval.
2. Generate tasks from that revision, record them, and get approval.
3. Build and test. Each task records one fixed Result.
4. Check the Brief acceptance list when the outcome is ready.

## install

```sh
curl -fsSL https://raw.githubusercontent.com/varelycode/ggez/main/scripts/install.sh | sh
```

Requires macOS or Linux, Python 3.9+, and curl.

## use it

```sh
ggez init
ggez --version
ggez plan "my next feature"
ggez revise brief
ggez revise tasks
ggez check
ggez status
```

Feature arguments are optional; ggez selects the only feature or offers fuzzy selection. `init` previews templates and scoped agent rules. `revise` records metadata without rewriting definitions. `check` and `status` are read-only.

Update an installed CLI with `ggez update`.

See the [working agreement](docs/workflow.md) and [agent rules](AGENTS.md).
