"""Parse-validity tests for tracked JSON, TOML, and YAML configs.

- JSON: strict json.loads, except the files editors treat as JSONC
  (comments, trailing commas), which get a tolerant parse -- and only
  those, so JSONC syntax can't creep into strict-JSON files.
- TOML: stdlib tomllib.
- YAML: yamllint with the policy in ~/.yamllint (relaxed profile:
  validity and duplicate keys, not style).
"""

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Editors read these as JSONC: comments and trailing commas allowed
JSONC_FILES = {
    ".claude/keybindings.json",
    ".config/zed/settings.json",
    ".vscode/extensions.json",
    ".vscode/settings.json",
    ".zed/settings.json",
    "Library/Application Support/Code/User/settings.json",
}


def tracked(pattern):
    proc = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", pattern],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.splitlines()


JSON_FILES = tracked("*.json")
TOML_FILES = tracked("*.toml")
YAML_FILES = tracked("*.yaml") + tracked("*.yml")


def strip_jsonc(text):
    """Remove // and /* */ comments (outside strings) and trailing commas."""
    out = []
    i = 0
    in_string = False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            i += 1
            continue
        if text.startswith("//", i):
            newline = text.find("\n", i)
            i = len(text) if newline == -1 else newline
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
            continue
        out.append(char)
        i += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(out))


@pytest.mark.parametrize("path", JSON_FILES)
def test_json_parses(path):
    text = (REPO / path).read_text()
    if path in JSONC_FILES:
        text = strip_jsonc(text)
    json.loads(text)


@pytest.mark.parametrize("path", TOML_FILES)
def test_toml_parses(path):
    tomllib.loads((REPO / path).read_text())


def test_yaml_lint_clean():
    if shutil.which("yamllint") is None:
        pytest.skip("yamllint not installed")
    proc = subprocess.run(
        ["yamllint", "-c", str(REPO / ".yamllint"), *YAML_FILES],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout
