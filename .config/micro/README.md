# Micro Editor Configuration

A lightweight terminal editor configured to feel like VS Code.
Installed via Homebrew (`brew install micro`).

## What is tracked

| File | Purpose |
| ---- | ------- |
| `settings.json` | Editor options and per-filetype tab sizes |
| `bindings.json` | VS Code-style keybinding overrides |
| `plug/fzfopen/` | Local plugin: Ctrl+P fuzzy file open via `fzf` |

Third-party plugins, `buffers/`, and `backups/` are not tracked.

## New machine setup

Micro creates its state directories on first run.
Install the one third-party plugin this config expects:

```sh
micro -plugin install filemanager
```

The `fzfopen` plugin arrives with the dotfiles and requires `fzf`
(already a Homebrew package in dev-machine-setup).

## Opening a whole directory

Micro opens files, not directories.
To work on a project:
`cd` into it, run `micro`, then use **Ctrl+P** (fuzzy open, respects
the current directory) or **Ctrl+B** (file tree sidebar).
Set `filemanager-openonstart` to `true` in `settings.json`
to always start with the tree open.

## Keybindings

Micro's defaults already match VS Code for the basics —
these work out of the box with no configuration:

| Key | Action |
| --- | ------ |
| Ctrl+S / Ctrl+Q | Save / quit (close current tab or split) |
| Ctrl+C / Ctrl+X / Ctrl+V | Copy / cut / paste (line-wise with no selection) |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| Ctrl+F, then Ctrl+N | Find, then find next |
| Ctrl+A | Select all |
| Alt+Up / Alt+Down | Move line up / down |
| Alt+Shift+Up / Down | Add cursor above / below |
| Ctrl+T, Alt+, / Alt+. | New tab, previous / next tab |
| Ctrl+E | Command bar (closest thing to the command palette) |
| Shift+arrows, mouse | Select text |

Overrides added in `bindings.json`:

| Key | Action | VS Code equivalent |
| --- | ------ | ------------------ |
| Ctrl+P | Fuzzy file open (`fzfopen` plugin) | Quick Open |
| Ctrl+B | Toggle file tree (`filemanager` plugin) | Toggle sidebar |
| Ctrl+D | Add cursor at next occurrence of selection | Same |
| Alt+D | Duplicate line (replaces the default Ctrl+D) | Shift+Alt+Down |
| Ctrl+/ | Toggle comment (terminals send it as Ctrl+_) | Same |
| Ctrl+G | Go to line | Same |
| F1 | Help (frees Ctrl+G, keeps the status-line hint working) | Same |

Rebound defaults you lose (and their replacements):
find-previous was Ctrl+P (still reachable: Ctrl+F, then Ctrl+N cycles forward),
and shell prompt was Ctrl+B (use `Ctrl+E` then `!command` instead).
Help moved from Ctrl+G to F1.

Terminal limitation: Ctrl+Shift combos are indistinguishable from plain Ctrl,
so VS Code chords like Ctrl+Shift+P cannot be bound.

## File tree (filemanager plugin)

Toggle with Ctrl+B or `> tree`.
Inside the tree: Tab or click opens a file or enters a directory,
arrow keys expand and collapse.
It registers `touch`, `mkdir`, `rename`, and `rm` commands
that operate on the highlighted entry.
