#!/usr/bin/env bash
# Run `phantom check --strict --format sarif` over files and directories and
# write the SARIF log to a file, for upload to GitHub code scanning.
#
# Usage: scripts/sarif_check.sh OUTPUT.sarif [PATH...]
# Environment:
#   PHANTOM_STRICT   "true" (default) adds --strict
#   PHANTOM_EXCLUDE  space-separated shell patterns of files to skip
#   PHANTOM_ARGS     extra arguments for `phantom check`
#   PHANTOM_PATHS    files/directories to check (used when no PATH is given)
# Exit code is the `phantom check` exit code (2 on findings/errors, 0 clean);
# the SARIF file is written either way, so an upload step can run with
# `if: always()` and still report the findings.
set -uo pipefail
export PYTHONIOENCODING=utf-8
export LC_ALL=C.UTF-8

output="${1:-}"
if [ -z "$output" ]; then
  echo "usage: sarif_check.sh OUTPUT.sarif [PATH...]" >&2
  exit 2
fi
shift

strict="${PHANTOM_STRICT:-true}"
exclude="${PHANTOM_EXCLUDE:-}"
extra="${PHANTOM_ARGS:-}"

raw_paths=()
if [ "$#" -gt 0 ]; then
  raw_paths=("$@")
elif [ -n "${PHANTOM_PATHS:-}" ]; then
  if [[ "$PHANTOM_PATHS" == *$'\n'* ]]; then
    while IFS= read -r line; do
      [ -n "$line" ] && raw_paths+=("$line")
    done <<< "$PHANTOM_PATHS"
  elif [ -e "$PHANTOM_PATHS" ]; then
    raw_paths+=("$PHANTOM_PATHS")
  else
    read -ra raw_paths <<< "$PHANTOM_PATHS"
  fi
else
  echo "usage: sarif_check.sh OUTPUT.sarif PATH [PATH...]" >&2
  exit 2
fi

excluded() {
  local file="$1" pattern
  local patterns=()
  if [[ "$exclude" == *$'\n'* ]]; then
    while IFS= read -r pattern; do
      [ -n "$pattern" ] && patterns+=("$pattern")
    done <<< "$exclude"
  else
    read -ra patterns <<< "$exclude"
  fi
  for pattern in "${patterns[@]}"; do
    # shellcheck disable=SC2053
    if [[ "$file" == $pattern ]]; then
      return 0
    fi
  done
  return 1
}

files=()
for path in "${raw_paths[@]}"; do
  if [ -d "$path" ]; then
    while IFS= read -r -d '' file; do
      files+=("$file")
    done < <(find "$path" -type f -name '*.py' \
      -not -path '*/.*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' \
      -not -path '*/venv/*' -not -path '*/.venv/*' -print0 | sort -z)
  elif [ -f "$path" ]; then
    files+=("$path")
  else
    echo "::error::path not found: $path" >&2
    exit 2
  fi
done

checked=()
for file in "${files[@]}"; do
  if ! excluded "$file"; then
    checked+=("$file")
  fi
done

if [ "${#checked[@]}" -eq 0 ]; then
  echo "phantom: no Python files to check" >&2
  exit 2
fi

flags=()
if [ "$strict" = "true" ]; then
  flags+=(--strict)
fi
# shellcheck disable=SC2206
flags+=($extra)

set +e
phantom check --format sarif "${flags[@]}" "${checked[@]}" > "$output"
code=$?
set -e
echo "phantom: checked ${#checked[@]} file(s), wrote $output (check exit $code)"
exit "$code"
