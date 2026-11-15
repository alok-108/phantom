#!/usr/bin/env bash
# Run `phantom check` over files and directories; exit non-zero if any file fails.
#
# Usage: scripts/ci_check.sh PATH [PATH...]
# Environment:
#   PHANTOM_STRICT   "true" (default) adds --strict (invisible / bidirectional characters)
#   PHANTOM_EXCLUDE  space-separated shell patterns of files to skip (matched against the path)
#   PHANTOM_ARGS     extra arguments for `phantom check`, e.g. "--deny cap.counters"
# Used by the composite GitHub Action in action.yml; also handy locally and in pre-commit.
set -uo pipefail

# Force UTF-8 encoding across Windows/Linux environments
export PYTHONIOENCODING=utf-8
export LC_ALL=C.UTF-8

strict="${PHANTOM_STRICT:-true}"
exclude="${PHANTOM_EXCLUDE:-}"
extra="${PHANTOM_ARGS:-}"

# Parse PHANTOM_PATHS or positional arguments into raw_paths array
raw_paths=()
if [ "$#" -gt 0 ]; then
  raw_paths=("$@")
elif [ -n "${PHANTOM_PATHS:-}" ]; then
  if [[ "$PHANTOM_PATHS" == *$'\n'* ]]; then
    while IFS= read -r line; do
      [ -n "$line" ] && raw_paths+=("$line")
    done <<< "$PHANTOM_PATHS"
  else
    # If there are no newlines, check if the whole string exists as a single file/directory first
    if [ -e "$PHANTOM_PATHS" ]; then
      raw_paths+=("$PHANTOM_PATHS")
    else
      # Otherwise, fall back to space-separated splitting
      read -ra raw_paths <<< "$PHANTOM_PATHS"
    fi
  fi
else
  echo "usage: ci_check.sh PATH [PATH...]" >&2
  exit 2
fi

flags=()
if [ "$strict" = "true" ]; then
  flags+=(--strict)
fi
# shellcheck disable=SC2206  # intentional word splitting of PHANTOM_ARGS
flags+=($extra)

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
    # shellcheck disable=SC2053  # the pattern is meant to be a glob
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

failed=0
checked=0
for file in "${files[@]}"; do
  if excluded "$file"; then
    continue
  fi
  checked=$((checked + 1))
  if ! phantom check "${flags[@]}" "$file"; then
    echo "::error file=$file::phantom check failed"
    failed=$((failed + 1))
  fi
done

echo "phantom: checked $checked file(s), $failed failed"
if [ "$failed" -gt 0 ]; then
  exit 1
fi
