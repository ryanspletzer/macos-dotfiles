@{
    # Script module or binary module file associated with this manifest.
    RootModule = 'Profile.psm1'

    # Version number of this module.
    ModuleVersion = '1.0.0'

    # Supported PSEditions
    CompatiblePSEditions = @('Desktop', 'Core')

    # ID used to uniquely identify this module
    GUID = '5c25eb98-0667-45fc-b321-f137097be7d8'

    # Author of this module
    Author = 'Ryan Spletzer'

    # Company or vendor of this module
    CompanyName = 'Personal'

    # Copyright statement for this module
    Copyright = '(c) 2025 Ryan Spletzer. All rights reserved.'

    # Description of the functionality provided by this module
    Description = 'Personal PowerShell profile module containing custom functions and aliases'

    # Minimum version of the Windows PowerShell engine required by this module
    PowerShellVersion = '5.1'

    # Functions to export from this module, for best performance, do not use wildcards and do not delete the entry, use an empty array if there are no functions to export.
    FunctionsToExport = @(
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
    )

    # Cmdlets to export from this module, for best performance, do not use wildcards and do not delete the entry, use an empty array if there are no cmdlets to export.
    CmdletsToExport = @()

    # Variables to export from this module
    VariablesToExport = @()

    # Aliases to export from this module, for best performance, do not use wildcards and do not delete the entry, use an empty array if there are no aliases to export.
    AliasesToExport = @(
        'openremote',
        'syncremote',
        'finder',
        'TextEdit',
        'caf'
    )

    # DSC resources to export from this module
    DscResourcesToExport = @()

    # List of all modules packaged with this module
    ModuleList = @()

    # List of all files packaged with this module
    FileList = @()

    # Private data to pass to the module specified in RootModule/ModuleToProcess. This may also contain a PSData hashtable with additional module metadata used by PowerShell.
    PrivateData = @{
        PSData = @{
            # Tags applied to this module. These help with module discovery in online galleries.
            Tags = @('Profile', 'Personal', 'Git', 'Utilities', 'macOS')

            # A URL to the license for this module.
            # LicenseUri = ''

            # A URL to the main website for this project.
            # ProjectUri = ''

            # A URL to an icon representing this module.
            # IconUri = ''

            # ReleaseNotes of this module
            # ReleaseNotes = ''

            # Prerelease string of this module
            # Prerelease = ''

            # Flag to indicate whether the module requires explicit user acceptance for install/update
            # RequireLicenseAcceptance = $false

            # External dependent modules of this module
            # ExternalModuleDependencies = @()
        } # End of PSData hashtable
    } # End of PrivateData hashtable

    # HelpInfo URI of this module
    # HelpInfoURI = ''

    # Default prefix for commands exported from this module. Override the default prefix using Import-Module -Prefix.
    # DefaultCommandPrefix = ''
}
