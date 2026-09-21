# ~/git

This is Ryan Spletzer's git parent directory.
Every repo he clones lives directly under here, e.g. `~/git/some-project`.
He picked `~/git` because it's descriptive,
and `git` is short enough to type without complaint.

He also sometimes wants to make sweeping configuration changes across all of
these repos at once,
for example rolling out a new Claude Code setting or convention to every
project under `~/git`.

## Why this file is tracked in git

`~/git` lives inside Ryan's home-folder dotfiles repo (`~`),
which uses an ignore-everything-then-selectively-un-ignore `.gitignore`
strategy.
By default `~/git/*` (every cloned repo) is ignored,
but this file is explicitly un-ignored so it can be
version-controlled as configuration,
separate from the repos it sits alongside.

## AGENTS.md is the only instruction file

Claude Code 2.1.277+ reads `AGENTS.md` natively when no `CLAUDE.md`
exists in the working directory or any directory above it.
Other AI coding tools already read `AGENTS.md` directly.
Nothing here or in `~` is named `CLAUDE.md`,
and that must stay true:
a `CLAUDE.md` in `~/git` or `~` would take precedence
and silently hide every `AGENTS.md` beneath it.

When setting up a new repo under `~/git`,
or updating an existing one,
give it a single `AGENTS.md` that describes that repo,
not this directory,
and do not add a `CLAUDE.md` symlink or file.
Claude Code loads this file and `~/AGENTS.md` through the
parent-directory walk-up in every session under `~/git`;
the other tools stop at the repo root.
