"""Cross-tool agent-CLI wiring consistency.

~/AGENTS.md is the tool-neutral instruction core, ~/.agents holds the
shared enforcement hooks and skills, and .claude/.codex/.cursor wire
them per tool. These tests assert the wiring points at files that
exist and that the tools stay in sync where they are meant to:

- every ~/.agents/hooks/*.py referenced by a tool's hook config exists
- Claude Code and Codex wire the identical set of shared hooks
  (Cursor goes through adapters by design and is not compared)
- the per-tool dotfiles-reference skill symlinks resolve to the
  canonical ~/.agents copy
- @~/path references in tracked instruction files resolve
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

HOOK_CONFIGS = [
    ".claude/settings.json",
    ".codex/hooks.json",
    ".cursor/hooks.json",
]

SKILL_LINKS = [
    ".claude/skills/dotfiles-reference",
    ".codex/skills/dotfiles-reference",
    ".cursor/skills/dotfiles-reference",
]

CANONICAL_SKILL = ".agents/skills/dotfiles-reference"

# Claude/Codex reference shared hooks as ~/.agents/...; Cursor's
# hooks.json uses ../.agents/... relative to its ~/.cursor location.
# Both resolve to .agents/... under the repo root.
HOOK_REF = re.compile(r"(?:~|\.\.)/(\.agents/hooks/[\w./-]+\.py)")


def tracked(pattern):
    proc = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", pattern],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.splitlines()


def hook_refs(config):
    return set(HOOK_REF.findall((REPO / config).read_text()))


@pytest.mark.parametrize("config", HOOK_CONFIGS)
def test_referenced_hook_scripts_exist(config):
    refs = hook_refs(config)
    assert refs, f"no ~/.agents/hooks references found in {config}"
    missing = sorted(ref for ref in refs if not (REPO / ref).is_file())
    assert missing == [], f"{config} references missing scripts: {missing}"


def test_claude_and_codex_wire_the_same_hooks():
    claude = {r for r in hook_refs(".claude/settings.json") if "/adapters/" not in r}
    codex = {r for r in hook_refs(".codex/hooks.json") if "/adapters/" not in r}
    assert claude == codex, (
        f"claude-only: {sorted(claude - codex)}; codex-only: {sorted(codex - claude)}"
    )


@pytest.mark.parametrize("link", SKILL_LINKS)
def test_skill_symlink_resolves_to_canonical(link):
    path = REPO / link
    assert path.is_symlink(), f"{link} is not a symlink"
    assert path.resolve() == (REPO / CANONICAL_SKILL).resolve()
    assert (path / "SKILL.md").is_file()


def test_at_references_resolve():
    # ~ is this repo's root, so resolve against REPO rather than the
    # running user's home -- in CI the checkout is not the home dir
    broken = []
    for md in tracked("*.md"):
        text = (REPO / md).read_text()
        for ref in re.findall(r"@~/([\w./-]+)", text):
            if not (REPO / ref).exists():
                broken.append(f"{md} -> @~/{ref}")
    assert broken == []
