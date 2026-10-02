#!/usr/bin/env bash
# check_pii.sh — Verify no PII leaks into non-data output files.
#
# False-positive exclusions:
#   *.pyc          — compiled bytecode cache of source files (not output)
#   __pycache__/   — same
#   Files where the account number appears ONLY inside a pii_terms list
#                    or an assertion that it is absent from output
#
# Usage: bash check_pii.sh          (run from loanlens-bundle/)

set -euo pipefail

# Split literal so this script doesn't match its own grep
PATTERN="8399060""0004041"

# Step 1: find all non-JSON, non-pyc files that contain the pattern
CANDIDATES=$(grep -rlE "$PATTERN" . 2>/dev/null \
  | grep -v "\.json$" \
  | grep -v "__pycache__" \
  | grep -v "\.pyc$" \
  || true)

# Step 2: from those candidates, drop files where every match is a
#         known-safe reference (pii_terms list or "not in" assertion)
LEAKS=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # Check if the file has any line with the pattern that is NOT a safe reference
  UNSAFE=$(grep -E "$PATTERN" "$f" \
    | grep -vE "(pii_terms|assert.*not in|not in.*assert)" \
    || true)
  if [ -n "$UNSAFE" ]; then
    LEAKS="$LEAKS\n  $f"
  fi
done <<< "$CANDIDATES"

echo "==================================="
if [ -z "$LEAKS" ]; then
  echo "✅ No PII in non-data files"
else
  echo "❌ PII found in:"
  echo -e "$LEAKS"
  exit 1
fi
echo "==================================="
