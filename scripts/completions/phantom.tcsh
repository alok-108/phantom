# tcsh completion for the Phantom command-line interface.
#
# Install by sourcing this file from your ~/.tcshrc:
#   source /path/to/phantom/scripts/completions/phantom.tcsh
#
# The current CLI exposes check, inspect, run, generate, diff and verify.
# Version is a global option (--version / -V), not a subcommand.
#
# After that, in a new shell:
#   phantom <TAB>            -> check inspect run generate diff verify ...
#   phantom check -<TAB>     -> only the flags check accepts
#   phantom check --format <TAB> -> text sarif

# Flags each subcommand accepts. The completion below reads the one that
# matches the subcommand on the command line, so `phantom run --<TAB>` never
# offers a flag that belongs to generate.
set _phantom_subcommands = (check inspect run generate diff verify)
set _phantom_global_flags = (-h --help --version -V --no-color)
set _phantom_check_flags = (-h --help -q --quiet --strict --format --deny --allow-only)
set _phantom_inspect_flags = (-h --help --json --strict --deny --allow-only)
set _phantom_run_flags = (-h --help -q --quiet --timeout --max-output --deny --allow-only --handlers-from --allow-handler)
set _phantom_generate_flags = (-h --help --stdin --intent --placement --encoding --output -o --dry-run --provider --plan-file --allow-remote)
set _phantom_diff_flags = (-h --help --host-only --exit-code --no-color)
set _phantom_verify_flags = (-h --help --timeout --max-output --args --stdin-file)
set _phantom_capabilities = (cap.stdio cap.events cap.diagnostics cap.counters cap.metadata)

# Rules are tried in order and the first match wins: flag values first, then
# the subcommand slot, then flags scoped to the subcommand, then filenames.
complete phantom \
    'n/--format/(text sarif)/' \
    'n/--encoding/(comment whitespace unicode)/' \
    'n/--placement/(beginning end main-guard line: near:)/' \
    'n/--provider/(gemini)/' \
    'n/--deny/$_phantom_capabilities/' \
    'n/--allow-only/$_phantom_capabilities/' \
    'n/--handlers-from/d/' \
    'n/--output/f/' \
    'n/-o/f/' \
    'n/--plan-file/f/' \
    'n/--stdin-file/f/' \
    'p/1/`echo $_phantom_subcommands $_phantom_global_flags`/' \
    'n/--no-color/$_phantom_subcommands/' \
    'C/-/`if ("$COMMAND_LINE" =~ "* check *") echo $_phantom_check_flags; if ("$COMMAND_LINE" =~ "* inspect *") echo $_phantom_inspect_flags; if ("$COMMAND_LINE" =~ "* run *") echo $_phantom_run_flags; if ("$COMMAND_LINE" =~ "* generate *") echo $_phantom_generate_flags; if ("$COMMAND_LINE" =~ "* diff *") echo $_phantom_diff_flags; if ("$COMMAND_LINE" =~ "* verify *") echo $_phantom_verify_flags`/' \
    'p/*/f/'
