# ggez

Write a Brief, approve tasks, build with evidence, then review.

## Install

macOS/Linux, Python 3.9+ and curl. Once this installer lands on `main`:

```sh
curl -fsSL https://raw.githubusercontent.com/varelycode/ggez/main/scripts/install.sh | sh
```

From a checkout now: `sh scripts/install.sh --source "$PWD"`.
Follow the printed PATH instruction.

### Existing project

Run `ggez init` in your project. Review and confirm. Existing rules stay; edited managed files require resolution.

### Fresh project

Run `mkdir my-project && cd my-project && ggez init`.

## Use

- `ggez plan "My feature"`: create a blank Brief and get an agent prompt.
- `ggez plan`: select a feature or create one.
- `ggez status`: show recorded progress and the next action.

You fill Slice and Outcome. Verified pauses after each task; explicitly choose Unverified to continue. Both require tests and evidence.

[Workflow](docs/workflow.md). No runner or automatic usage collection is included.
