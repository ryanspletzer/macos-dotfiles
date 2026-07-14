"""PowerShell profile and module verification.

Runs pwsh as a subprocess for three layers:

- PSScriptAnalyzer over the profiles and Profile module, with policy
  in ~/.config/powershell/PSScriptAnalyzerSettings.psd1
- Test-ModuleManifest on the Profile module manifest
- a clean-session import of the Profile module
"""

import functools
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PWSH_DIR = ".config/powershell"
MODULE_DIR = f"{PWSH_DIR}/Modules/Profile/1.0.0"
SETTINGS = f"{PWSH_DIR}/PSScriptAnalyzerSettings.psd1"

ANALYZED_FILES = [
    f"{PWSH_DIR}/Microsoft.PowerShell_profile.ps1",
    f"{PWSH_DIR}/Microsoft.VSCode_profile.ps1",
    f"{MODULE_DIR}/Profile.psm1",
    f"{MODULE_DIR}/Profile.psd1",
    f"{MODULE_DIR}/Profile.Tests.ps1",
]

pytestmark = pytest.mark.skipif(
    shutil.which("pwsh") is None, reason="pwsh not installed"
)


def pwsh(script, timeout=180):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@functools.lru_cache(maxsize=1)
def has_scriptanalyzer():
    proc = pwsh("if (Get-Module -ListAvailable PSScriptAnalyzer) { 'yes' }")
    return "yes" in proc.stdout


@pytest.mark.parametrize("path", ANALYZED_FILES)
def test_scriptanalyzer_clean(path):
    if not has_scriptanalyzer():
        pytest.skip("PSScriptAnalyzer not installed")
    script = (
        f"$findings = Invoke-ScriptAnalyzer -Path '{path}' -Settings '{SETTINGS}'; "
        "$findings | Format-Table RuleName, Line, Message -AutoSize "
        "| Out-String -Width 120 | Write-Output; "
        "exit @($findings).Count"
    )
    proc = pwsh(script)
    assert proc.returncode == 0, f"{path}:\n{proc.stdout}{proc.stderr}"


def test_module_manifest_is_valid():
    proc = pwsh(
        f"Test-ModuleManifest '{MODULE_DIR}/Profile.psd1' -ErrorAction Stop | Out-Null"
    )
    assert proc.returncode == 0, proc.stderr


def test_module_imports_cleanly():
    proc = pwsh(f"Import-Module './{MODULE_DIR}/Profile.psd1' -ErrorAction Stop")
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""


@functools.lru_cache(maxsize=1)
def has_pester():
    proc = pwsh("if (Get-Module -ListAvailable Pester) { 'yes' }")
    return "yes" in proc.stdout


def test_pester_suite_passes():
    if not has_pester():
        pytest.skip("Pester not installed")
    script = (
        "$config = New-PesterConfiguration; "
        f"$config.Run.Path = '{MODULE_DIR}'; "
        "$config.Run.Exit = $true; "
        "$config.Output.Verbosity = 'Detailed'; "
        "Invoke-Pester -Configuration $config"
    )
    proc = pwsh(script)
    assert proc.returncode == 0, proc.stdout + proc.stderr
