# Profile PowerShell Module
# Contains custom functions and aliases for personal use

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

function Start-Caffeination {
    [CmdletBinding()]
    param ()

    begin {}

    process {
        caffeinate -disu
    }

    end {}
}

# A wrapper for Get-MsalToken to get a token for Microsoft Graph using delegated permissions.
# Supports all the same parameters as Get-MsalToken
function Get-MgAccessTokenDelegated {
    [CmdletBinding()]
    [OutputType([string])]
    param (
        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $ClientId = '14d82eec-204b-4c2f-b7e8-296a70dab67e', # Microsoft Graph PowerShell SDK Client ID

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $TenantId,

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string[]]
        $Scopes = @('https://graph.microsoft.com/.default')
    )

    begin {}

    process {
        # Check if tenant ID is provided, if it is, add it to. Get-MsalToken params
        $params = @{
            ClientId = $ClientId
            Scopes   = $Scopes
        }
        if ($TenantId) {
            $params.TenantId = $TenantId
        }

        # Get the token using Get-MsalToken
        $token = Get-MsalToken @params
        if ($null -eq $token) {
            Write-Error "Failed to retrieve Microsoft Graph token."
            return
        }

        # Output the token
        $token.AccessToken
    }

    end {}
}

function Get-MgUserDirectReportTransitive {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]
        $UserId,

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string]
        $AccessToken
    )

    begin {
        # If an access token is provided, call Connect-MgGraph with it
        if ($AccessToken) {
            Connect-MgGraph -AccessToken $AccessToken -ErrorAction Stop
        } else {
            # Otherwise, ensure the user is connected to Microsoft Graph
            if (-not (Get-MgContext)) {
                Write-Error "You must be connected to Microsoft Graph to use this function."
                return
            }
        }
    }

    process {
        $directReports = Get-MgUserDirectReport -UserId $UserId -All
        foreach ($report in $directReports) {
            # Escape hatch to avoid infinite recursion, e.g. someone reporting to themselves
            # (It does happen)
            if ($report.Id -eq $UserId) {
                continue
            }

            # Output the direct report
            $report
            Get-MgUserDirectReportTransitive -UserId $report.Id
        }
    }

    end {}
}

# Create aliases
New-Alias -Name openremote -Value Open-GitRemoteUrl
New-Alias -Name syncremote -Value Sync-GitOriginRemoteFromUpstream
New-Alias -Name finder -Value Open-Finder
New-Alias -Name TextEdit -Value Open-TextEdit
New-Alias -Name caf -Value Start-Caffeination

# Export functions and aliases
Export-ModuleMember -Function @(
    'Open-GitRemoteUrl',
    'Sync-GitOriginRemoteFromUpstream',
    'Get-TypeAccelerators',
    'Open-Finder',
    'Open-TextEdit',
    'Get-LocalCertificate',
    'Use-Pyenv',
    'Get-ParentItem',
    'Find-ParentFilePath',
    'Enter-PyenvDir',
    'Exit-PyenvDir',
    'Start-Caffeination',
    'Get-MgAccessTokenDelegated',
    'Get-MgUserDirectReportTransitive'
) -Alias @(
    'openremote',
    'syncremote',
    'finder',
    'TextEdit',
    'caf'
)
