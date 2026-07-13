"""Unit tests for _utils.strip_quoted_content."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _utils import strip_quoted_content  # noqa: E402


def test_strips_single_quoted_strings():
    assert "pip install" not in strip_quoted_content("echo 'pip install x'")


def test_strips_double_quoted_strings():
    assert "pip install" not in strip_quoted_content('echo "pip install x"')


def test_respects_escaped_double_quotes():
    result = strip_quoted_content('echo "a \\" pip install b"')
    assert "pip install" not in result


def test_strips_heredoc_content():
    cmd = "cat <<EOF\npip install requests\nEOF"
    assert "pip install" not in strip_quoted_content(cmd)


def test_strips_comments():
    assert "pip install" not in strip_quoted_content("ls  # pip install x")


def test_preserves_real_command_tokens():
    assert strip_quoted_content("pip install requests") == "pip install requests"


def test_preserves_tokens_outside_quotes():
    result = strip_quoted_content("pip install 'requests'")
    assert result.startswith("pip install")
