# Nushell completion for phantom.
#
# Install by sourcing this file in your Nushell config (config.nu), e.g.:
#   source scripts/completions/phantom.nu
# Or use it as an imported module:
#   use scripts/completions/phantom.nu *
#
# A new shell then completes subcommands and flags, e.g.:
#   phantom <TAB>         -> check, inspect, run, generate, diff, verify
#   phantom check --<TAB> -> --strict, --format, --deny, --allow-only
#   phantom run --<TAB>   -> --timeout, --deny, --allow-only, ...

def "nu-complete phantom format" [] {
    [ "text", "json", "sarif" ]
}

def "nu-complete phantom encoding" [] {
    [ "comment", "whitespace", "unicode" ]
}

def "nu-complete phantom placement" [] {
    [ "beginning", "end", "line:1", "main-guard" ]
}

# Dual-layer Python programming system: ordinary Python + typed instruction layer
export extern "phantom" [
    --help(-h)                   # Show help
    --version(-V)                # Show version
    --no-color                   # Omit ANSI color escapes from output
]

# Check and validate Phantom instructions in one or more files
export extern "phantom check" [
    --help(-h)                   # Show help
    --quiet(-q)                  # Suppress non-error output
    --strict                     # Also report invisible/bidirectional code points outside zero-width blocks
    --format: string@"nu-complete phantom format" # Output format (text, json, sarif)
    --deny: string               # Deny capability CAP (repeatable)
    --allow-only: string         # Allow ONLY capability CAP (repeatable)
    ...file: path                # Source file(s) to check
]

# Inspect Phantom instructions without executing
export extern "phantom inspect" [
    --help(-h)                   # Show help
    --json                       # Output instructions in JSON format
    --strict                     # List suspicious invisible code points (exit 2 if any)
    --deny: string               # Deny capability CAP (repeatable)
    --allow-only: string         # Allow ONLY capability CAP (repeatable)
    file: path                   # Source file to inspect
]

# Validate and run host program with Phantom runtime
export extern "phantom run" [
    --help(-h)                   # Show help
    --quiet(-q)                  # Suppress non-error output
    --timeout: float             # Host program timeout in seconds (default: 30.0)
    --max-output: int            # Per-stream host output cap in bytes
    --deny: string               # Deny capability CAP (repeatable)
    --allow-only: string         # Allow ONLY capability CAP (repeatable)
    --handlers-from: path        # Only import event handlers from DIR (repeatable)
    --allow-handler: string      # Pattern for allowed handlers (fnmatch)
    file: path                   # Source file to run
    ...host_args: string         # Arguments passed to the host program
]

# Generate Phantom instructions using LLM
export extern "phantom generate" [
    --help(-h)                   # Show help
    --stdin                      # Read the program from stdin
    --intent: string             # What the Phantom layer should do
    --placement: string@"nu-complete phantom placement" # Placement strategy
    --encoding: string@"nu-complete phantom encoding" # Target encoding (comment, whitespace, unicode)
    --output(-o): path           # Write the candidate here
    --dry-run                    # Show the diff; write nothing
    --provider: string           # LLM provider (default: gemini)
    --model: string              # Model name
    --plan-file: path            # Use this local JSON plan instead of calling a provider
    --allow-remote               # Consent to sending the source to the remote provider
    file?: path                  # Source file to augment
]

# Unified diff between two source files
export extern "phantom diff" [
    --help(-h)                   # Show help
    --host-only                  # Compare only the Python host layer, excluding Phantom instructions
    --phantom-only               # Compare only the Phantom instruction layer
    --exit-code                  # Exit with 0 if equal, 1 if different, and 2 on usage or file errors
    --no-color                   # Omit ANSI color escapes from the diff
    original: path               # Original file
    candidate: path              # Candidate file
]

# Compare runtime behavior of two programs
export extern "phantom verify" [
    --help(-h)                   # Show help
    --timeout: float             # Per-program timeout in seconds
    --max-output: int            # Per-stream host output cap in bytes
    --args: string               # Repeatable arg group passed to both programs
    --stdin-file: path           # Stdin file supplied to both runs
    original: path               # Original program file
    candidate: path              # Candidate program file
]
