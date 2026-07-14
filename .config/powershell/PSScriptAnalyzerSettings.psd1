@{
    # Lint policy for the profile scripts and Profile module.
    # These are interactive-session helpers, not a published module,
    # so console-oriented and help-related rules are excluded.
    ExcludeRules = @(
        # Profiles write status text to the console by design
        'PSAvoidUsingWriteHost',
        # Session helpers, not a documented public API
        'PSProvideCommentHelp',
        # Profiles define session-global helpers intentionally
        'PSAvoidGlobalFunctions',
        # Interactive convenience wrappers around git/launchctl
        'PSUseShouldProcessForStateChangingFunctions',
        # Terse interactive invocations are acceptable in profiles
        'PSAvoidUsingPositionalParameters',
        # Names like Get-MgUserDirectReportTransitive follow Graph nouns
        'PSUseSingularNouns',
        # oh-my-posh init's documented bootstrap pattern
        'PSAvoidUsingInvokeExpression'
    )
}
