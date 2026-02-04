$env:GPG_TTY=$(tty)

$env:PSModulePath += ':' + $HOME + '/.config/powershell/Modules'

Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView
Set-PSReadLineOption -EditMode Windows
Set-PSReadlineOption -BellStyle None

$env:HOMEBREW_PREFIX = '/opt/homebrew'
$env:HOMEBREW_CELLAR = '/opt/homebrew/Cellar'
$env:HOMEBREW_REPOSITORY = '/opt/homebrew'
$env:PATH = $('/opt/homebrew/bin:/opt/homebrew/sbin:'+$env:PATH)
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
