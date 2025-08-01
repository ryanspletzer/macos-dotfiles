# Profile Module

This is a personal PowerShell module containing custom functions and aliases for macOS.

## Functions

### Git Functions

- `Open-GitRemoteUrl` (Alias: `openremote`) - Opens the remote Git repository URL in the default browser
- `Sync-GitOriginRemoteFromUpstream` (Alias: `syncremote`) - Syncs the origin remote from upstream

### System Utilities

- `Open-Finder` (Alias: `finder`) - Opens the specified directory in Finder
- `Open-TextEdit` (Alias: `TextEdit`) - Opens the specified file in TextEdit
- `Start-Caffeination` (Alias: `caf`) - Prevents the system from sleeping
- `Get-TypeAccelerators` - Gets PowerShell type accelerators
- `Get-LocalCertificate` - Gets certificates from the local certificate store

### Python Environment Management

- `Use-Pyenv` - Activates a specific Python version using pyenv
- `Enter-PyenvDir` - Auto-activates pyenv version based on .python-version file
- `Exit-PyenvDir` - Deactivates the current pyenv version

### File System Utilities

- `Get-ParentItem` - Gets the parent directory of the specified path
- `Find-ParentFilePath` - Finds a file by searching up the directory tree

### Microsoft Graph Utilities

- `Get-MgAccessTokenDelegated` - Gets a delegated access token for Microsoft Graph
- `Get-MgUserDirectReportTransitive` - Gets all direct reports transitively for a user

## Installation

This module is designed to be used as part of a personal PowerShell profile. It should be located in your PowerShell modules path.

## Requirements

- PowerShell 5.1 or later
- macOS (some functions are macOS-specific)
- Git (for Git-related functions)
- pyenv (for Python environment functions)
- Microsoft.Graph PowerShell SDK (for Graph functions)
