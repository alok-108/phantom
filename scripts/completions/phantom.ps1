# PowerShell completion for phantom.
#
# Install by dot-sourcing this file from $PROFILE, e.g.:
#   . scripts/completions/phantom.ps1
# A new shell then completes subcommands and flags, e.g.:
#   phantom <TAB>         -> check, inspect, run, generate, diff, verify
#   phantom check --<TAB> -> --strict, --format, --deny, --allow-only
#   phantom run --<TAB>   -> --timeout, --deny, --allow-only, ...
Register-ArgumentCompleter -CommandName 'phantom' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $tokens = $commandAst.ToString() -split '\s+'
    $subcommand = $null
    foreach ($token in $tokens) {
        if ($token -in @('check', 'inspect', 'run', 'generate', 'diff', 'verify')) {
            $subcommand = $token
            break
        }
    }
    $globalFlags = @('-h', '--help', '--version', '-V', '--no-color')
    if (-not $subcommand) {
        $candidates = @('check', 'inspect', 'run', 'generate', 'diff', 'verify') + $globalFlags
        return $candidates | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
    }
    # check
    if ($subcommand -eq 'check') {
        $flags = @('-h', '--help', '--strict', '--format', '--deny', '--allow-only')
        $values = @('text', 'sarif')
        if ($wordToComplete -like '--format*') { $values = @('text', 'sarif') }
        $candidates = $flags + $values
    }
    # inspect
    elseif ($subcommand -eq 'inspect') {
        $flags = @('-h', '--help', '--json', '--strict', '--deny', '--allow-only')
        $candidates = $flags
    }
    # run
    elseif ($subcommand -eq 'run') {
        $flags = @('-h', '--help', '--timeout', '--deny', '--allow-only', '--handlers-from', '--allow-handler')
        $candidates = $flags
    }
    # generate
    elseif ($subcommand -eq 'generate') {
        $flags = @('-h', '--help', '--stdin', '--intent', '--placement', '--encoding', '--output', '-o', '--dry-run', '--provider', '--plan-file', '--allow-remote')
        $values = @('comment', 'whitespace', 'unicode')
        $candidates = $flags + $values
    }
    # diff
    elseif ($subcommand -eq 'diff') {
        $flags = @('-h', '--help', '--host-only', '--no-color')
        $candidates = $flags
    }
    # verify
    elseif ($subcommand -eq 'verify') {
        $flags = @('-h', '--help', '--timeout')
        $candidates = $flags
    }
    else {
        $candidates = @()
    }
    return $candidates | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
