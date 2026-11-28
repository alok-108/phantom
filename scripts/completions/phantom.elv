# Elvish completion for the Phantom command-line interface.
#
# Install by sourcing this file from your Elvish rc.elv:
#   use ./scripts/completions/phantom
# Or source it directly:
#   source scripts/completions/phantom.elv
#
# The current CLI exposes check, inspect, run, generate, diff and verify.
# Version is a global option (--version / -V), not a subcommand. There is
# currently no decode subcommand.

set edit:completion:arg-completer[phantom] = {|@args|
    var n = (count $args)
    if (== $n 2) {
        put check inspect run generate diff verify
        put --help --version -V --no-color
    } elif (>= $n 3) {
        var subcommand = $args[2]
        var current = $args[-1]
        var previous = ''
        if (>= $n 4) {
            set previous = $args[-2]
        }

        if (== $previous --format) {
            put text sarif
        } elif (== $previous --encoding) {
            put comment whitespace unicode
        } elif (== $previous --placement) {
            put beginning end line:1 main-guard
        } elif (== $previous --provider) {
            put gemini
        } elif (== $previous --deny) {
            put cap.stdio cap.events cap.diagnostics cap.counters cap.metadata
        } elif (== $previous --allow-only) {
            put cap.stdio cap.events cap.diagnostics cap.counters cap.metadata
        } else {
            if (== $subcommand check) {
                put -h --help -q --quiet --strict --format --json --deny --allow-only
            } elif (== $subcommand inspect) {
                put -h --help --json --strict --deny --allow-only
            } elif (== $subcommand run) {
                put -h --help -q --quiet --timeout --max-output --deny --allow-only --handlers-from --allow-handler
            } elif (== $subcommand generate) {
                put -h --help --stdin --intent --placement --encoding --output -o --dry-run --provider --model --plan-file --allow-remote
            } elif (== $subcommand diff) {
                put -h --help --host-only --phantom-only --exit-code --no-color
            } elif (== $subcommand verify) {
                put -h --help --timeout --max-output --args --stdin-file
            }

            edit:complete-filename $current
        }
    }
}
