# ggez

ggez keeps feature work in two editable files: a Brief for the outcome and Tasks for implementation.

1. Fill Slice and Outcome in the [Brief](templates/prd.md).
2. Review and approve the [tasks](templates/tasks.md).
3. Build and test. Each task records one fixed Result.
4. Check the Brief acceptance list when the outcome is ready.

## install

```sh
curl -fsSL https://raw.githubusercontent.com/varelycode/ggez/main/scripts/install.sh | sh
```

Requires macOS or Linux, Python 3.9+, and curl.

## use it

Run these from a project folder:

```sh
ggez init
ggez plan "my next feature"
ggez status
```

`init` previews the templates and scoped agent rules before writing. `plan` creates a blank Brief. `status` reads approved documents without changing them.

Update an installed CLI without a checkout:

```sh
ggez update
```

See the [working agreement](docs/workflow.md) and [agent rules](AGENTS.md).
