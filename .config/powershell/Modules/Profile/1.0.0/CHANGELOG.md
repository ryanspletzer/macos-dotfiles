# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-01

### Added

- Initial release of the Profile module
- Git functions: `Open-GitRemoteUrl`, `Sync-GitOriginRemoteFromUpstream`
- System utilities: `Open-Finder`, `Open-TextEdit`, `Start-Caffeination`, `Get-TypeAccelerators`, `Get-LocalCertificate`
- Python environment management: `Use-Pyenv`, `Enter-PyenvDir`, `Exit-PyenvDir`
- File system utilities: `Get-ParentItem`, `Find-ParentFilePath`
- Microsoft Graph utilities: `Get-MgAccessTokenDelegated`, `Get-MgUserDirectReportTransitive`
- Aliases: `openremote`, `syncremote`, `finder`, `TextEdit`, `caf`
- Module manifest (Profile.psd1)
- Documentation (README.md)

### Changed

- Extracted functions and aliases from PowerShell profile into proper module structure

### Removed

- Functions and aliases moved from PowerShell profile to module
