#compdef phantom
# zsh completion for phantom.
#
# Install by copying or symlinking this file to a directory on $fpath
# (e.g. ~/.zsh/completions/_phantom) and running
# `autoload -Uz compinit && compinit`, then start a new shell:
#   phantom <TAB>         -> check, inspect, run, generate, diff, verify
#   phantom check --<TAB> -> --strict, --format, --deny, --allow-only
#   phantom run --<TAB>   -> --timeout, --deny, --allow-only, ...

_phantom() {
    local context state line
    typeset -A opt_args

    local -a subcommands
    subcommands=(
        'check:Check and validate Phantom instructions in a file'
        'inspect:Inspect Phantom instructions without executing'
        'run:Validate and run host program with Phantom runtime'
        'generate:Generate Phantom instructions using LLM'
        'diff:Unified diff between two source files'
        'verify:Compare runtime behavior of two programs'
    )

    _arguments -C \
        '(-h --help)'{-h,--help}'[show help]' \
        '(--version -V)'{--version,-V}"[show program's version]" \
        '--no-color[omit ANSI color escapes from output]' \
        '1:subcommand:->subcommand' \
        '*::args:->args'

    case $state in
        subcommand)
            _describe -t subcommands 'phantom subcommand' subcommands
            ;;
        args)
            case $line[1] in
                # check
                check)
                    _arguments \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--strict[also report invisible/bidirectional code points outside zero-width blocks]' \
                        '--format[output format]:format:(text sarif)' \
                        '--deny[deny a capability]:capability:' \
                        '--allow-only[grant only these capabilities]:capability:' \
                        '1:file:_files'
                    ;;
                # inspect
                inspect)
                    _arguments \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--json[output instructions in JSON format]' \
                        '--strict[list suspicious invisible code points]' \
                        '--deny[deny a capability]:capability:' \
                        '--allow-only[grant only these capabilities]:capability:' \
                        '1:file:_files'
                    ;;
                # run
                run)
                    _arguments \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--timeout[host program timeout in seconds]:timeout:' \
                        '--deny[deny a capability]:capability:' \
                        '--allow-only[grant only these capabilities]:capability:' \
                        '--handlers-from[only import event handlers from DIR]:directory:_files -/' \
                        '--allow-handler[also allow handlers matching PATTERN]:pattern:' \
                        '1:file:_files' \
                        '*:host args:'
                    ;;
                # generate
                generate)
                    _arguments \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--stdin[read the program from stdin]' \
                        '--intent[what the Phantom layer should do]:intent:' \
                        '--placement[where to place new instructions]:placement:' \
                        '--encoding[instruction encoding]:encoding:(comment whitespace unicode)' \
                        '(-o --output)'{-o,--output}'[write the candidate here]:output:_files' \
                        '--dry-run[show the diff; write nothing]' \
                        '--provider[LLM provider]:provider:' \
                        '--plan-file[use this local JSON plan instead of calling a provider]:plan file:_files' \
                        '--allow-remote[consent to sending the source to the remote provider]' \
                        '1:file:_files'
                    ;;
                # diff
                diff)
                    _arguments \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--host-only[compare only the Python host layer]' \
                        '--exit-code[exit with 1 if different, 2 on usage or file errors]' \
                        '--no-color[omit ANSI color escapes from the diff]' \
                        '1:original:_files' \
                        '2:candidate:_files'
                    ;;
                # verify
                verify)
                    _arguments \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--timeout[per-program timeout in seconds]:timeout:' \
                        '1:original:_files' \
                        '2:candidate:_files'
                    ;;
            esac
            ;;
    esac
}
