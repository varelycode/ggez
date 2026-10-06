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

## start a feature

got something in mind?

```sh
ggez plan "my next feature"
```

this creates a blank brief and prints a prompt.

1. fill in the required parts of the brief.
2. copy the prompt into your coding agent to keep going (ง •̀_•́)ง

already started something? leave out the title to pick a feature from the list, or choose “new feature” to start another.

```console
$ ggez plan
1. dark-mode
2. login
0. New feature
Choose a number, or Enter to cancel:
```

pick a number to keep going, or `0` to start something new. selecting a feature prints the full path to its brief and the agent prompt; it doesn’t open the file.

## see where things stand

```sh
ggez status
```

check your current task, how much is done, and recorded run time when available.

here’s an example with one of two tasks finished:

```console
$ ggez status
Feature: login
Current task: TASK-2 — add login form
Stage: Implementation
Completed: 1/2 (50%)
Execution time: Unavailable (no execution records)
brief.md: /home/ana/my-project/features/login/brief.md
tasks.md: /home/ana/my-project/features/login/tasks.md
evidence.md: /home/ana/my-project/features/login/evidence.md
```

no timing data? it’ll say so.

See the [working agreement](docs/workflow.md) and [agent rules](AGENTS.md).
