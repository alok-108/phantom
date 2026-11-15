# tcsh completion for phantom.
#
# Install by sourcing this file from ~/.tcshrc, e.g.:
#   source scripts/completions/phantom.tcsh
# A new shell then completes subcommands and flags, e.g.:
#   phantom <TAB>         -> check, inspect, decode, run, generate, ...
#   phantom check --<TAB> -> --strict, --format, --help
#   phantom run --<TAB>   -> --timeout, --deny, --allow-only, ...

# The first word is a subcommand (or a global option). Flags that take a
# fixed set of values complete those values next. Each subcommand is then
# followed by its own flags, and anything else completes as a filename.
complete phantom \
    'p/1/(check inspect decode run generate diff verify version -h --help --version -V --no-color)/' \
    'n/--format/(text sarif)/' \
    'n/--mode/(comment whitespace unicode hybrid)/' \
    'n/--encoding/(comment whitespace unicode)/' \
    'n/--placement/(beginning end line:1 main-guard)/' \
    'n/--provider/(gemini)/' \
    'n/--deny/(cap.stdio cap.events cap.diagnostics cap.counters cap.metadata)/' \
    'n/--allow-only/(cap.stdio cap.events cap.diagnostics cap.counters cap.metadata)/' \
    'n/--handlers-from/d/' \
    'n/--output/f/' \
    'n/-o/f/' \
    'n/--plan-file/f/' \
    'n/--stdin-file/f/' \
    'n/check/(-h --help -q --quiet --strict --format --deny --allow-only)/' \
    'n/inspect/(-h --help --json --strict --deny --allow-only)/' \
    'n/decode/(-h --help --strict --format --mode)/' \
    'n/run/(-h --help -q --quiet --timeout --max-output --deny --allow-only --handlers-from --allow-handler)/' \
    'n/generate/(-h --help --stdin --intent --placement --encoding --output -o --dry-run --provider --model --plan-file --allow-remote)/' \
    'n/diff/(-h --help --host-only --phantom-only --exit-code --no-color)/' \
    'n/verify/(-h --help --timeout --max-output --args --stdin-file)/' \
    'n/version/(-h --help --version)/' \
    'c/--/(help strict format mode version no-color quiet json timeout max-output deny allow-only handlers-from allow-handler stdin intent placement encoding output dry-run provider model plan-file allow-remote host-only phantom-only exit-code args stdin-file)/' \
    'c/-/(h V q o)/' \
    'p/*/f/'
