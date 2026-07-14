$env:GPG_TTY=$(tty)

# Autodesk Artifactory npm token (from Keychain)
$npmToken = security find-generic-password -s npm-autodesk-token -w 2>$null
if ($npmToken) { $env:NPM_AUTODESK_TOKEN = $npmToken }

# ngrok auth token (from Keychain)
$ngrokToken = security find-generic-password -s ngrok -a authtoken -w 2>$null
if ($ngrokToken) { $env:NGROK_AUTHTOKEN = $ngrokToken }

$env:PSModulePath += ':' + $HOME + '/.config/powershell/Modules'

Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView
Set-PSReadLineOption -EditMode Windows
Set-PSReadlineOption -BellStyle None

# Make Shift+Enter accept the line like Enter (Ghostty sends modified sequences)
Set-PSReadLineKeyHandler -Chord 'Shift+Enter' -Function AcceptLine

$env:HOMEBREW_PREFIX = '/opt/homebrew'
$env:HOMEBREW_CELLAR = '/opt/homebrew/Cellar'
$env:HOMEBREW_REPOSITORY = '/opt/homebrew'
$env:PATH = $('/opt/homebrew/bin:/opt/homebrew/sbin:'+$env:PATH)
$env:PATH += ':' + $HOME + '/.dotnet/tools'
$env:PATH += ':' + $HOME + '/.cargo/bin'
$env:PATH += ':' + $HOME + '/.local/bin'
$env:PNPM_HOME = Join-Path $HOME "Library/pnpm"
$env:PATH = (Join-Path $env:PNPM_HOME "bin") + [IO.Path]::PathSeparator + $env:PATH
$env:BUN_INSTALL = Join-Path $HOME ".bun"
$env:PATH = (Join-Path $env:BUN_INSTALL "bin") + [IO.Path]::PathSeparator + $env:PATH
$env:MANPATH = $('/opt/homebrew/share/man'+$(if(${env:MANPATH}){':'+${env:MANPATH}})+':')
$env:INFOPATH = $('/opt/homebrew/share/info'+$(if(${env:INFOPATH}){':'+${env:INFOPATH}}))

Import-Module -Name Profile

if ("$env:TERM_PROGRAM" -ne "Apple_Terminal") {
    oh-my-posh init pwsh --config "~/.oh-my-posh/themes/mytheme.yaml" | Invoke-Expression
    Import-Module -Name Terminal-Icons
} else {
    Import-Module -Name posh-git
}

# PowerShell parameter completion shim for the dotnet CLI
Register-ArgumentCompleter -Native -CommandName dotnet -ScriptBlock {
    param (
        $commandName,
        $wordToComplete,
        $cursorPosition
    )

    # Positional signature is fixed by Register-ArgumentCompleter; only
    # the latter two arguments are needed by 'dotnet complete'.
    $null = $commandName

    dotnet complete --position $cursorPosition "$wordToComplete" | ForEach-Object -Process {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}

# Set up pyenv auto-activation/deactivation when changing directories
$ExecutionContext.InvokeCommand.LocationChangedAction = {
    # Deactivate previous version
    global:Exit-PyenvDir

    # Activate new version if needed
    global:Enter-PyenvDir
}
