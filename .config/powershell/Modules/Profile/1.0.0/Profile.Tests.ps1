#Requires -Modules Pester

<#
    .SYNOPSIS
        Behavioral Pester tests for the Profile module.

    .DESCRIPTION
        Scope: pure logic (throttle math, path walking), module surface
        (declared functions callable, aliases mapped), PATH manipulation
        (pyenv helpers), and mocked-git behavior for Sync-GitRemote and
        the git wrappers.

        Functions that only launch external applications (Open-Finder,
        Start-Emacs, ...) and the Microsoft Graph wrappers (require live
        MSAL/Graph) are exercised through the surface tests only.

    .EXAMPLE
        Invoke-Pester -Path ~/.config/powershell/Modules/Profile/1.0.0
#>

BeforeDiscovery {
    $script:manifest = Import-PowerShellDataFile -Path (Join-Path $PSScriptRoot 'Profile.psd1')
}

BeforeAll {
    Import-Module -Name (Join-Path $PSScriptRoot 'Profile.psd1') -Force
}

Describe 'Module surface' {
    It 'makes declared function <_> callable' -ForEach $manifest.FunctionsToExport {
        Get-Command -Name $_ -ErrorAction SilentlyContinue | Should -Not -BeNullOrEmpty
    }

    It 'maps declared alias <_> to an existing function' -ForEach $manifest.AliasesToExport {
        $alias = Get-Alias -Name $_ -ErrorAction SilentlyContinue
        $alias | Should -Not -BeNullOrEmpty
        Get-Command -Name $alias.Definition -ErrorAction SilentlyContinue | Should -Not -BeNullOrEmpty
    }

    It 'keeps the muscle-memory aliases pointed at the right functions' {
        (Get-Alias -Name syncremote).Definition | Should -Be 'Sync-GitRemote'
        (Get-Alias -Name openremote).Definition | Should -Be 'Open-GitRemoteUrl'
        (Get-Alias -Name code).Definition | Should -Be 'Open-VSCode'
        (Get-Alias -Name gs).Definition | Should -Be 'Get-GitStatus'
    }
}

Describe 'Get-ParallelThrottle' {
    It 'returns the core count for a CPU workload' {
        InModuleScope -ModuleName Profile {
            $cores = [Environment]::ProcessorCount
            $expected = [math]::Min([math]::Max($cores, 2), 64)
            Get-ParallelThrottle -Workload CPU | Should -Be $expected
        }
    }

    It 'returns 2x cores rounded up for an IO workload' {
        InModuleScope -ModuleName Profile {
            $cores = [Environment]::ProcessorCount
            $expected = [math]::Min([math]::Max([math]::Ceiling($cores * 2), 2), 64)
            Get-ParallelThrottle -Workload IO | Should -Be $expected
        }
    }

    It 'defaults to 1.5x cores rounded up (Mixed)' {
        InModuleScope -ModuleName Profile {
            $cores = [Environment]::ProcessorCount
            $expected = [math]::Min([math]::Max([math]::Ceiling($cores * 1.5), 2), 64)
            Get-ParallelThrottle | Should -Be $expected
        }
    }

    It 'clamps to -Max' {
        InModuleScope -ModuleName Profile {
            Get-ParallelThrottle -Workload IO -Max 2 | Should -Be 2
        }
    }

    It 'raises to -Min when the computed value is lower' {
        InModuleScope -ModuleName Profile {
            Get-ParallelThrottle -Workload CPU -Min 1000 -Max 2000 | Should -Be 1000
        }
    }
}

Describe 'Get-ParentItem' {
    It 'returns the parent directory of a path' {
        $child = New-Item -ItemType Directory -Path (Join-Path $TestDrive 'a' 'b') -Force
        (Get-ParentItem -Path $child.FullName).Name | Should -Be 'a'
    }

    It 'handles multiple paths' {
        $childA = New-Item -ItemType Directory -Path (Join-Path $TestDrive 'a' 'b') -Force
        $childC = New-Item -ItemType Directory -Path (Join-Path $TestDrive 'c' 'd') -Force
        $parents = Get-ParentItem -Path $childA.FullName, $childC.FullName
        $parents.Name | Should -Be @('a', 'c')
    }

    It 'returns nothing for a bare name with no parent component' {
        Get-ParentItem -Path 'orphan' | Should -BeNullOrEmpty
    }
}

Describe 'Find-ParentFilePath' {
    BeforeEach {
        $script:deep = New-Item -ItemType Directory -Path (Join-Path $TestDrive 'a' 'b' 'c') -Force
        $script:marker = New-Item -ItemType File -Path (Join-Path $TestDrive 'a' 'probe-marker.txt') -Force
    }

    It 'walks up to the nearest ancestor containing the file' {
        Find-ParentFilePath -Name 'probe-marker.txt' -Path $deep.FullName |
            Should -Be $marker.FullName
    }

    It 'returns the file from the starting directory when present there' {
        Find-ParentFilePath -Name 'probe-marker.txt' -Path $marker.Directory.FullName |
            Should -Be $marker.FullName
    }

    It 'returns nothing when no ancestor contains the file' {
        $name = "no-such-file-$([guid]::NewGuid()).txt"
        Find-ParentFilePath -Name $name -Path $deep.FullName | Should -BeNullOrEmpty
    }
}

Describe 'pyenv helpers' {
    BeforeEach {
        $script:savedPath = $env:PATH
    }

    AfterEach {
        $env:PATH = $script:savedPath
    }

    It 'Use-Pyenv prepends the version bin dir when the version exists' {
        Mock -CommandName Test-Path -ModuleName Profile -MockWith { $true }
        Use-Pyenv -Version '9.9.9'
        ($env:PATH -split ':')[0] | Should -Be "$HOME/.pyenv/versions/9.9.9/bin"
    }

    It 'Use-Pyenv leaves PATH alone when the version is absent' {
        Mock -CommandName Test-Path -ModuleName Profile -MockWith { $false }
        Use-Pyenv -Version '9.9.9'
        $env:PATH | Should -Be $savedPath
    }

    It 'Exit-PyenvDir strips pyenv version segments and keeps the rest' {
        $env:PATH = "/usr/bin:$HOME/.pyenv/versions/1.2.3/bin:/bin"
        Exit-PyenvDir
        $env:PATH | Should -Be '/usr/bin:/bin'
    }

    It 'Enter-PyenvDir activates the version named in .python-version' {
        Mock -CommandName Use-Pyenv -ModuleName Profile -MockWith {}
        Push-Location -Path $TestDrive
        try {
            Set-Content -Path '.python-version' -Value '9.9.9'
            Enter-PyenvDir
        } finally {
            Pop-Location
        }
        Should -Invoke -CommandName Use-Pyenv -ModuleName Profile -Times 1 -Exactly -ParameterFilter {
            $Version -eq '9.9.9'
        }
    }
}

Describe 'Sync-GitRemote' {
    It 'switches to trunk, force-deletes the branch, pulls origin, and prunes' {
        Mock -CommandName git -ModuleName Profile -MockWith {
            switch -Regex (($args -join ' ')) {
                '^branch --show-current$' { 'feature-x' }
                '^branch$' { @('  feature-x', '* main') }
                default { $null }
            }
        }

        Sync-GitRemote -Force

        foreach ($expected in @(
            'checkout main',
            'branch -D feature-x',
            'pull origin main',
            'remote prune origin'
        )) {
            Should -Invoke -CommandName git -ModuleName Profile -Times 1 -Exactly -ParameterFilter {
                ($args -join ' ') -eq $expected
            }
        }
        Should -Invoke -CommandName git -ModuleName Profile -Times 0 -Exactly -ParameterFilter {
            ($args -join ' ') -eq 'push'
        }
    }

    It 'stays put and keeps the branch when already on trunk' {
        Mock -CommandName git -ModuleName Profile -MockWith {
            switch -Regex (($args -join ' ')) {
                '^branch --show-current$' { 'main' }
                '^branch$' { @('* main') }
                default { $null }
            }
        }

        Sync-GitRemote

        Should -Invoke -CommandName git -ModuleName Profile -Times 0 -Exactly -ParameterFilter {
            ($args -join ' ') -like 'checkout*'
        }
        Should -Invoke -CommandName git -ModuleName Profile -Times 0 -Exactly -ParameterFilter {
            ($args -join ' ') -like 'branch -D*'
        }
        Should -Invoke -CommandName git -ModuleName Profile -Times 1 -Exactly -ParameterFilter {
            ($args -join ' ') -eq 'pull origin main'
        }
    }

    It 'pulls from upstream and pushes back to the fork when upstream exists' {
        Mock -CommandName git -ModuleName Profile -MockWith {
            switch -Regex (($args -join ' ')) {
                '^branch --show-current$' { 'main' }
                '^branch$' { @('* main') }
                '^remote get-url upstream$' { 'git@github.com:upstream/repo.git' }
                default { $null }
            }
        }

        Sync-GitRemote

        Should -Invoke -CommandName git -ModuleName Profile -Times 1 -Exactly -ParameterFilter {
            ($args -join ' ') -eq 'pull upstream main'
        }
        Should -Invoke -CommandName git -ModuleName Profile -Times 1 -Exactly -ParameterFilter {
            ($args -join ' ') -eq 'push'
        }
    }
}

Describe 'git wrappers' {
    It '<Name> invokes git as <Expected>' -ForEach @(
        @{ Name = 'Get-GitDiff'; Extra = @('--stat', 'HEAD~1'); Expected = 'diff --stat HEAD~1' }
        @{ Name = 'Get-GitDiffColored'; Extra = @(); Expected = 'diff --color=always' }
        @{ Name = 'Get-GitStatus'; Extra = @('-s'); Expected = 'status -s' }
        @{ Name = 'Get-GitStatusColored'; Extra = @(); Expected = '-c color.status=always status' }
    ) {
        Mock -CommandName git -ModuleName Profile -MockWith {}
        & $Name @Extra
        # Filter out $null: splatting an unset $Arguments passes a literal
        # $null to the mock that native command invocation would drop
        Should -Invoke -CommandName git -ModuleName Profile -Times 1 -Exactly -ParameterFilter {
            (($args | Where-Object { $null -ne $_ }) -join ' ') -eq $Expected
        }
    }
}

Describe 'Get-TypeAccelerators' {
    It 'returns the accelerator dictionary including psobject' {
        (Get-TypeAccelerators).Keys | Should -Contain 'psobject'
    }
}

Describe 'Get-LocalCertificate' {
    It 'reads the CurrentUser/My store without error' {
        { Get-LocalCertificate } | Should -Not -Throw
    }
}
