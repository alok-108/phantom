# bash completion for phantom.
#
# Install by sourcing this file from ~/.bashrc, or by copying or
# symlinking it into bash-completion's completions directory, e.g.:
#   ~/.local/share/bash-completion/completions/phantom
# A new shell then completes subcommands and flags, e.g.:
#   phantom <TAB>         -> check, inspect, run, generate, diff, verify
#   phantom check --<TAB> -> --strict, --format, --deny, --allow-only
#   phantom run --<TAB>   -> --timeout, --deny, --allow-only, ...

_phantom() {
    local cur prev subcommand
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    subcommand="${COMP_WORDS[1]}"

    # Values for flags that take a fixed set of values.
    case "$prev" in
        --format)
            COMPREPLY=( $(compgen -W "text sarif" -- "$cur") )
            return 0
            ;;
        --encoding)
            COMPREPLY=( $(compgen -W "comment whitespace unicode" -- "$cur") )
            return 0
            ;;
        --deny|--allow-only|--timeout|--handlers-from|--allow-handler|--intent|--placement|--output|-o|--provider|--plan-file)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
    esac

    # Before a subcommand: offer the subcommands, plus the global flags
    # (--version and --no-color only apply before a subcommand is given).
    if [[ "$COMP_CWORD" -eq 1 ]]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $(compgen -W "-h --help --version -V --no-color" -- "$cur") )
        else
            COMPREPLY=( $(compgen -W "check inspect run generate diff verify" -- "$cur") )
        fi
        return 0
    fi

    # After a subcommand: offer only that subcommand's flags (or files
    # for its positional arguments).
    if [[ "$cur" != -* ]]; then
        COMPREPLY=( $(compgen -f -- "$cur") )
        return 0
    fi
    case "$subcommand" in
        # check
        check)
            COMPREPLY=( $(compgen -W "-h --help --strict --format --deny --allow-only" -- "$cur") )
            ;;
        # inspect
        inspect)
            COMPREPLY=( $(compgen -W "-h --help --json --strict --deny --allow-only" -- "$cur") )
            ;;
        # run
        run)
            COMPREPLY=( $(compgen -W "-h --help --timeout --deny --allow-only --handlers-from --allow-handler" -- "$cur") )
            ;;
        # generate
        generate)
            COMPREPLY=( $(compgen -W "-h --help --stdin --intent --placement --encoding --output -o --dry-run --provider --plan-file --allow-remote" -- "$cur") )
            ;;
        # diff
        diff)
            COMPREPLY=( $(compgen -W "-h --help --host-only --exit-code --no-color" -- "$cur") )
            ;;
        # verify
        verify)
            COMPREPLY=( $(compgen -W "-h --help --timeout" -- "$cur") )
            ;;
    esac
    return 0
}

complete -F _phantom phantom
