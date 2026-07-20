# Helix Editor Configuration

A modal terminal editor (Kakoune-style selection-first editing)
with built-in LSP, tree-sitter, and pickers — no plugins needed.
Installed via Homebrew (`brew install helix`, binary is `hx`).

Unlike the micro setup, Helix cannot be made to feel like VS Code —
it is modal by design.
This config keeps Helix's native model
and adds a few VS Code-flavored conveniences on top.

## What is tracked

| File | Purpose |
| ---- | ------- |
| `config.toml` | Editor options, theme, and keybinding overrides |
| `languages.toml` | Per-filetype 2-space indents mirroring VS Code |

Everything else under `.config/helix/` stays untracked.
Editor state lives outside this directory
(`~/.local/state/helix`, `~/.cache/helix`).

## New machine setup

Nothing beyond `brew install helix` — there are no plugins.
Language servers come from the usual dev-machine-setup packages;
run `hx --health` to see which ones Helix finds.

## VS Code-flavored overrides

Added in `config.toml`:

| Key | Action | VS Code equivalent |
| --- | ------ | ------------------ |
| Ctrl+S | Save (works in insert mode too) | Save |
| Ctrl+P | Fuzzy file picker | Quick Open |
| Ctrl+B | File explorer | Toggle sidebar |
| Ctrl+/ | Toggle comment (normal and select modes) | Same |

Also set: `dark_plus` theme (Helix's port of VS Code Dark+),
bufferline (tabs) when multiple buffers are open,
bar cursor in insert mode, indent guides,
and dotfiles visible in the file picker.

Rebound defaults you lose:
Ctrl+S was save-selection-to-jumplist,
and Ctrl+B was page up (PageUp and Ctrl+U still scroll up).

Note on the file picker in this home-folder repo:
Ctrl+P respects `.gitignore`,
and this repo ignores everything by default,
so in `~` the picker only shows tracked files.
Use Ctrl+B (the explorer browses everything) or `:open <path>` for the rest.

## Coming from VS Code: the essentials

| Key | Action |
| --- | ------ |
| `i` / `Esc` | Enter insert mode / back to normal mode |
| `Space` | Leader menu (pickers, LSP actions — discoverable) |
| `Space` `?` | Command palette |
| `:42` | Go to line 42 |
| `u` / `U` | Undo / redo |
| `x` | Select line (repeat to extend) |
| `%` | Select whole file (Ctrl+A) |
| `y` / `d` / `p` | Copy / cut / paste the selection |
| `Space` `y` / `Space` `p` | Copy / paste via system clipboard |
| `Ctrl+C` | Toggle comment (Helix default, kept) |
| `C` | Add cursor on the line below (multi-cursor) |
| `s` | Select all regex matches within selection (then edit all at once) |
| `*` then `n` | Search for current selection, jump to next match |
| `gd` / `Space` `k` / `Space` `r` | Go to definition / hover docs / rename symbol |
| `/` | Search |

The closest thing to VS Code's Ctrl+D workflow:
select a word (`miw`), then `*` to make it the search pattern,
then `v` and `n` to extend, or use `s` on a larger selection
to get a cursor on every match.

## Where things live

- Tutorial: run `hx --tutor`
- Health check (LSP servers, clipboard, tree-sitter): `hx --health`
- Default keymap reference: `:help` or <https://docs.helix-editor.com/keymap.html>
