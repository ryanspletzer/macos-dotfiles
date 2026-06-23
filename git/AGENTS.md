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
but this file and `CLAUDE.md` are explicitly un-ignored so they can be
version-controlled as configuration,
separate from the repos they sit alongside.

## CLAUDE.md / AGENTS.md symlink pattern

`CLAUDE.md` in this directory is a symlink to this file (`AGENTS.md`).
This file is the canonical source;
`CLAUDE.md` exists only so Claude Code picks it up automatically.
Other AI coding tools that look for `AGENTS.md` instead read this file
directly.
Because file reads transparently follow symlinks,
both tools see identical content with only one file to maintain.

This directory is a worked example of that pattern, not a template to be
copied verbatim.
When setting up a new repo under `~/git`,
or updating an existing one,
AI tools should replicate the *pattern* — a canonical `AGENTS.md` with a
`CLAUDE.md` symlink pointing to it — rather than copying this file's
content.
Each repo's `AGENTS.md` should describe that repo,
not this directory.
