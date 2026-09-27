"""Cross-tool agent-CLI wiring consistency.

~/.agents/AGENTS.md is the tool-neutral instruction core, ~/AGENTS.md
holds home-repo notes only, ~/.agents holds the shared enforcement hooks
and skills, and .claude/.codex/.cursor/.copilot/.gemini wire them per
tool. These tests assert the wiring points at files that
exist and that the tools stay in sync where they are meant to:

- every ~/.agents/hooks/*.py referenced by a tool's hook config exists
- Claude Code and Codex wire the identical set of shared hooks
  (Cursor goes through adapters by design and is not compared)
- every shared skill in ~/.agents/skills has a SKILL.md and a per-skill
  symlink in the Claude and Codex skill dirs that resolves to it
- the Cursor and Antigravity skill dirs are whole-directory symlinks to
  ~/.agents/skills (those tools keep no tool-managed extras there)
- @~/path references in tracked instruction files resolve
- the per-tool global instruction symlinks resolve to ~/.agents/AGENTS.md
- no CLAUDE.md sits at the repo root or in ~/git, so Claude Code
  (2.1.277+) reads AGENTS.md natively in ~ and every session beneath it
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

SHARED_SKILLS = ".agents/skills"

# Claude Code and Codex keep tool-managed extras beside the shared skills
# (Claude: humanizer, powershell-style, synced; Codex: .system), so they
# get one symlink per skill. Cursor and Antigravity hold nothing else, so
# their skills dir is a single symlink to the shared tree.
PER_SKILL_LINK_DIRS = [".claude/skills", ".codex/skills"]
WHOLE_DIR_LINKS = [".cursor/skills", ".gemini/config/skills"]


def shared_skills():
    return sorted(
        p.name for p in (REPO / SHARED_SKILLS).iterdir() if p.is_dir()
    )

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


@pytest.mark.parametrize("skill", shared_skills())
def test_shared_skill_has_skill_md(skill):
    assert (REPO / SHARED_SKILLS / skill / "SKILL.md").is_file()


@pytest.mark.parametrize("link_dir", PER_SKILL_LINK_DIRS)
@pytest.mark.parametrize("skill", shared_skills())
def test_skill_symlink_resolves_to_canonical(link_dir, skill):
    path = REPO / link_dir / skill
    assert path.is_symlink(), f"{link_dir}/{skill} is not a symlink"
    assert path.resolve() == (REPO / SHARED_SKILLS / skill).resolve()
    assert (path / "SKILL.md").is_file()


@pytest.mark.parametrize("link", WHOLE_DIR_LINKS)
def test_skills_dir_symlink_resolves_to_shared_tree(link):
    path = REPO / link
    assert path.is_symlink(), f"{link} is not a symlink"
    assert path.resolve() == (REPO / SHARED_SKILLS).resolve()
    assert sorted(p.name for p in path.iterdir() if p.is_dir()) == shared_skills()


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


INSTRUCTION_SYMLINKS = [
    ".codex/AGENTS.md",
    ".gemini/GEMINI.md",
    ".copilot/copilot-instructions.md",
]


@pytest.mark.parametrize("link", INSTRUCTION_SYMLINKS)
def test_instruction_symlink_resolves_to_global_core(link):
    path = REPO / link
    assert path.is_symlink(), f"{link} is not a symlink"
    assert path.resolve() == (REPO / ".agents/AGENTS.md").resolve()


@pytest.mark.parametrize(
    "name",
    ["CLAUDE.md", "CLAUDE.local.md", "git/CLAUDE.md", "git/CLAUDE.local.md"],
)
def test_no_root_claude_md(name):
    # Claude Code reads AGENTS.md only when no CLAUDE.md variant exists in
    # the working directory or above it; one at the ~ or ~/git level would
    # silently disable native AGENTS.md loading for every session beneath
    # it. ~/.claude/CLAUDE.md (user scope)
    # is exempt from that check and is expected to stay.
    assert not (REPO / name).exists(), f"{name} blocks native AGENTS.md loading"
