# fish shell completions for phantom.
#
# Install by copying or symlinking this file to:
#   ~/.config/fish/completions/phantom.fish
# A new fish shell then completes subcommands and flags, e.g.:
#   phantom <TAB>         -> check, inspect, run, generate, diff, verify
#   phantom check --<TAB> -> --strict, --format, --deny, --allow-only, ...
#   phantom run --<TAB>   -> --timeout, --deny, --allow-only, ...

# Subcommands
complete -c phantom -n "__fish_use_subcommand" -a check -d "Validate instruction layers without running"
complete -c phantom -n "__fish_use_subcommand" -a inspect -d "Display recognized instructions"
complete -c phantom -n "__fish_use_subcommand" -a run -d "Validate and run host program"
complete -c phantom -n "__fish_use_subcommand" -a generate -d "Propose Phantom instructions"
complete -c phantom -n "__fish_use_subcommand" -a diff -d "Show diff between files"
complete -c phantom -n "__fish_use_subcommand" -a verify -d "Compare behavior equivalence"

# Common options. -h/--help is offered by every subcommand; the global
# --version and --no-color only apply before a subcommand is given.
complete -c phantom -s h -l help -d "Show help"
complete -c phantom -n "__fish_use_subcommand" -s V -l version -d "Show version"
complete -c phantom -n "__fish_use_subcommand" -l no-color -d "Omit ANSI color escapes from output"

# check
complete -c phantom -n "__fish_seen_subcommand_from check" -l strict -d "Also report invisible/bidirectional code points outside zero-width blocks"
complete -c phantom -n "__fish_seen_subcommand_from check" -l format -d "Output format" -r -a "text sarif"
complete -c phantom -n "__fish_seen_subcommand_from check" -l deny -d "Deny a capability" -r
complete -c phantom -n "__fish_seen_subcommand_from check" -l allow-only -d "Grant only these capabilities" -r

# inspect
complete -c phantom -n "__fish_seen_subcommand_from inspect" -l json -d "Output instructions in JSON format"
complete -c phantom -n "__fish_seen_subcommand_from inspect" -l strict -d "List suspicious invisible code points"
complete -c phantom -n "__fish_seen_subcommand_from inspect" -l deny -d "Deny a capability" -r
complete -c phantom -n "__fish_seen_subcommand_from inspect" -l allow-only -d "Grant only these capabilities" -r

# run
complete -c phantom -n "__fish_seen_subcommand_from run" -l timeout -d "Host program timeout in seconds" -r
complete -c phantom -n "__fish_seen_subcommand_from run" -l deny -d "Deny a capability" -r
complete -c phantom -n "__fish_seen_subcommand_from run" -l allow-only -d "Grant only these capabilities" -r
complete -c phantom -n "__fish_seen_subcommand_from run" -l handlers-from -d "Only import event handlers from DIR" -r
complete -c phantom -n "__fish_seen_subcommand_from run" -l allow-handler -d "Also allow handlers matching PATTERN" -r

# generate
complete -c phantom -n "__fish_seen_subcommand_from generate" -l stdin -d "Read the program from stdin"
complete -c phantom -n "__fish_seen_subcommand_from generate" -l intent -d "What the Phantom layer should do" -r
complete -c phantom -n "__fish_seen_subcommand_from generate" -l placement -d "Where to place new instructions" -r
complete -c phantom -n "__fish_seen_subcommand_from generate" -l encoding -d "Instruction encoding" -r -a "comment whitespace unicode"
complete -c phantom -n "__fish_seen_subcommand_from generate" -s o -l output -d "Write the candidate here (never the input file)" -r
complete -c phantom -n "__fish_seen_subcommand_from generate" -l dry-run -d "Show the diff; write nothing"
complete -c phantom -n "__fish_seen_subcommand_from generate" -l provider -d "LLM provider" -r
complete -c phantom -n "__fish_seen_subcommand_from generate" -l plan-file -d "Use this local JSON plan instead of calling a provider" -r
complete -c phantom -n "__fish_seen_subcommand_from generate" -l allow-remote -d "Consent to sending the source to the remote provider"

# diff
complete -c phantom -n "__fish_seen_subcommand_from diff" -l host-only -d "Compare only the Python host layer"
complete -c phantom -n "__fish_seen_subcommand_from diff" -l exit-code -d "Exit with 1 if different, 2 on usage or file errors"
complete -c phantom -n "__fish_seen_subcommand_from diff" -l no-color -d "Omit ANSI color escapes from the diff"

# verify
complete -c phantom -n "__fish_seen_subcommand_from verify" -l timeout -d "Per-program timeout in seconds" -r
