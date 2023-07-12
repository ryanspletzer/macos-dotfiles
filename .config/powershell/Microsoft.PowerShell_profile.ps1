$env:GPG_TTY=$(tty)

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

Import-Module -Name posh-git

if ("$env:TERM_PROGRAM" -ne "Apple_Terminal") {
    oh-my-posh init pwsh --config "~/.oh-my-posh/themes/mytheme.json" | Invoke-Expression
    Import-Module -Name Terminal-Icons
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

function Open-GitRemoteUrl {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$false)]
        [string]
        $RemoteName = 'origin'
    )

    begin {}

    process {
        Start-Process -FilePath (git remote get-url $RemoteName)
    }

    end {}
}

New-Alias -Name openremote -Value Open-GitRemoteUrl

function Sync-GitOriginRemoteFromUpstream {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $false)]
        [ValidateNotNullOrEmpty()]
        [Alias('b')]
        [string]
        $Branch,

        [Parameter(Mandatory = $false)]
        [Alias('f')]
        [switch]
        $Force
    )

    begin {}

    process {
        $b = git branch --show-current
        $trunk = $null
        if ($b -notmatch '(main|master)') {
            if (git branch | Select-String -Pattern main) {
                $trunk = 'main'
                git checkout $trunk
            } else {
                $trunk = 'master'
                git checkout $trunk
            }

            if ($Force.IsPresent) {
                git branch -D $b
            }
        }

        if ($null -eq $trunk) {
            if ($null -eq (git branch | Select-String -Pattern 'main')) {
                $trunk = 'master'
            } else {
                $trunk = 'main'
            }
        }

        git pull upstream $trunk
        git push
        git remote prune origin
        if (-not [string]::IsNullOrEmpty($Branch)) {
            git branch -D $branch
        }
    }

    end {}
}

New-Alias -Name syncremote -Value Sync-GitOriginRemoteFromUpstream

function Get-TypeAccelerators {
    [CmdletBinding()]
    param ()

    begin {}

    process {
        [psobject].Assembly.GetType("System.Management.Automation.TypeAccelerators")::get
    }

    end {}
}

function Open-Finder {
    [CmdletBinding()]
    param (
        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $DirectoryPath = (Get-Location).Path
    )

    begin {
        $resolvedDirectoryPath = Resolve-Path -Path $DirectoryPath
    }

    process {
        open -a finder $DirectoryPath
    }

    end {}
}

New-Alias -Name finder -Value Open-Finder

function Get-LocalCertificate {
    [CmdletBinding()]
    [OutputType()]
    param ()

    begin {}

    process {
        $x509Store = [System.Security.Cryptography.X509Certificates.X509Store]::new(
            [System.Security.Cryptography.X509Certificates.StoreName]::My,
            [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser
        )
        $x509Store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)

        # Output
        $x509Store.Certificates

    }

    end {
        $x509Store.Close()
        $x509Store.Dispose()
    }
}
