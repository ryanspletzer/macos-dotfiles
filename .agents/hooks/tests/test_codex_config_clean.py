"""Tests for codex-config-clean.py, the .codex/config.toml git clean filter.

Codex-written machine state (project trust entries, hook trust hashes,
notice/nux counters) must be stripped; portable user settings (model,
[tui] status_line) must survive byte-identical so the filter is stable
under repeated application.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "codex-config-clean.py"

SAMPLE = """\
model = "gpt-5.4"
[projects."/Users/someone/git/scratch"]
trust_level = "trusted"

[notice.model_migrations]
"gpt-5.3-codex" = "gpt-5.4"

[tui]
status_line = [
  "model-with-reasoning",
  "current-dir",
]

[tui.model_availability_nux]
"gpt-5.6-sol" = 3

[hooks.state]

[hooks.state."/Users/someone/.codex/hooks.json:pre_tool_use:0:0"]
trusted_hash = "sha256:abc"
"""


def clean(text):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def test_strips_machine_state_sections():
    out = clean(SAMPLE)
    assert "projects" not in out
    assert "hooks.state" not in out
    assert "notice" not in out
    assert "model_availability_nux" not in out
    assert "/Users/" not in out


def test_keeps_portable_settings():
    out = clean(SAMPLE)
    assert 'model = "gpt-5.4"' in out
    assert "[tui]" in out
    assert '"model-with-reasoning"' in out


def test_idempotent():
    once = clean(SAMPLE)
    assert clean(once) == once


def test_empty_input():
    assert clean("") == ""
