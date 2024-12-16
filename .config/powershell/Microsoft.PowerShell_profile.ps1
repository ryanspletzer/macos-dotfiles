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
        open -a finder $resolvedDirectoryPath
    }

    end {}
}

New-Alias -Name finder -Value Open-Finder

function Open-TextEdit {
    [CmdletBinding()]
    param (
        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $FilePath
    )

    begin {
        $resolvedFilePath = Resolve-Path -Path $FilePath
    }

    process {
        open -a TextEdit $resolvedFilePath
    }

    end {}
}

New-Alias -Name TextEdit -Value Open-TextEdit

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

function Use-Pyenv {
    [CmdletBinding()]
    param (
        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $Version
    )

    begin {
        $pyenvRoot = "$HOME/.pyenv"
        $pyenvPython = "$pyenvRoot/versions/$Version/bin/python"
    }

    process {
        if (Test-Path -Path $pyenvPython) {
            $env:PATH = "$pyenvRoot/versions/$Version/bin:" + $env:PATH
            Write-Verbose -Message "Activated pyenv version $version"
        } else {
            Write-Verbose -Message "Python version $Version not found in pyenv."
        }
    }

    end {}
}

# TODO: handle upwards recursion for finding first .python-version file

function Get-ParentItem {
    [CmdletBinding()]
    [OutputType([System.IO.DirectoryInfo])]
    param (
        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string[]]
        $Path = @( '.' ),

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $Filter,

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string[]]
        $Include,

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string[]]
        $Exclude,

        [Parameter()]
        [switch]
        $Recurse,

        [Parameter()]
        [int]
        $Depth,

        [Parameter()]
        [switch]
        $Force
    )

    begin {}

    process {
        foreach ($currentPath in $Path) {
            $parentPath = Split-Path -Path $currentPath -Parent
            if ($parentPath) {
                # Output
                Get-Item -Path $parentPath
            }
        }
    }

    end {}
}

function Find-ParentFilePath {
    [CmdletBinding()]
    [OutputType([string])]
    param (
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]
        $Name,

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $Path = (Get-Location).Path
    )

    begin {}

    process {
        while ($Path -and -not (Test-Path -Path (Join-Path -Path $Path -ChildPath $Name))) {
            $Path = Split-Path -Path $Path -Parent
        }

        if ($Path) {
            # Output
            Join-Path -Path $Path -ChildPath $Name
        }
    }

    end {}
}

function global:Enter-PyenvDir {
    [CmdletBinding()]
    param ()

    begin {}

    process {
        if (Test-Path -Path '.python-version') {
            $pyversion = Get-Content -Path '.python-version'
            Use-Pyenv -Version $pyversion
        }
    }

    end {}
}

function global:Exit-PyenvDir {
    [CmdletBinding()]
    param ()

    begin {}

    process {
        # Reset PATH to remove the Python path
        $env:PATH = ($env:PATH -split ':') -notmatch "$HOME/.pyenv/versions/.*/bin" -join ':'
        Write-Verbose -Message 'Deactivated pyenv versions'
    }

    end {}
}

$ExecutionContext.InvokeCommand.LocationChangedAction = {
    # Deactivate previous version
    global:Exit-PyenvDir

    # Activate new version if needed
    global:Enter-PyenvDir
}
function Start-Caffeination {
    [CmdletBinding()]
    param ()

    begin {}

    process {
        caffeinate -disu
    }

    end {}
}

# Short hand so I don't have to type the full command
Set-Alias -Name caf -Value Start-Caffeination
