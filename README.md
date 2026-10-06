# ggez

1. **Describe it.** Fill in Slice and Outcome in a [Brief](templates/prd.md).
2. **Approve it.** Review and edit the [tasks](templates/tasks.md).
3. **Build it.** The agent follows approved tasks and records [Evidence](templates/evidence.md).
4. **Review it.** Check the outcome and leave feedback in [Review](templates/review.md).

## install the ggez cli :p

```sh
curl -fsSL https://raw.githubusercontent.com/varelycode/ggez/main/scripts/install.sh | sh
```

you’ll need macos or linux, python 3.9+, and curl. if the installer prints a PATH command, run that too. tiny bit of setup, then you’re in.

## get your project ready

new project or one you’ve been putting off finishing, run this from its folder:

```sh
ggez init
```

take a peek at the proposed changes, then confirm when you’re happy with them.

See the [working agreement](docs/workflow.md) and [agent rules](AGENTS.md).

## check progress

`ggez status` shows your task, stage, progress, recorded time, and file paths.
