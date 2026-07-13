"""Tests for filter-test-output.py, the test-runner output filter.

Simple test-runner invocations get rewritten to log-capture-and-filter
form with the real exit code preserved; everything else must pass
through untouched (the hook prints "{}").
"""

import json

from _harness import bash, run_hook

HOOK = "filter-test-output.py"


def output(proc):
    assert proc.returncode == 0
    return json.loads(proc.stdout)


def test_wraps_simple_pytest_run():
    proc = run_hook(HOOK, bash("uv run pytest tests/ -q"))
    hso = output(proc)["hookSpecificOutput"]
    new_cmd = hso["updatedInput"]["command"]
    assert hso["permissionDecision"] == "allow"
    assert "( uv run pytest tests/ -q )" in new_cmd
    assert "exit $__rc" in new_cmd  # real exit code preserved


def test_wraps_go_test():
    proc = run_hook(HOOK, bash("go test ./..."))
    new_cmd = output(proc)["hookSpecificOutput"]["updatedInput"]["command"]
    assert "( go test ./... )" in new_cmd


def test_leaves_chained_command_untouched():
    proc = run_hook(HOOK, bash("uv run pytest && echo done"))
    assert output(proc) == {}


def test_leaves_piped_command_untouched():
    proc = run_hook(HOOK, bash("uv run pytest | tail -5"))
    assert output(proc) == {}


def test_leaves_non_test_command_untouched():
    proc = run_hook(HOOK, bash("ls -la"))
    assert output(proc) == {}


def test_quoted_runner_mention_untouched():
    proc = run_hook(HOOK, bash('echo "uv run pytest"'))
    assert output(proc) == {}
