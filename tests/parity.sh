#!/usr/bin/env bash
# Walks every leaf in the spec, runs it through --dry-run in both frontends and
# diffs the two outputs. The two interpreters must agree on every command.
#
#   bash tests/parity.sh
#
# Normalisation: bash prints MSYS paths (/c/Users/...) where PowerShell prints
# C:/Users/..., and capture lines carry the current HH:MM.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

CONFIG="config/cli.json"
PWSH="${PWSH:-pwsh}"
FAILED=0
CHECKED=0

normalise() {
  sed -e "s#^/c/#C:/#" \
    -e "s#: /c/#: C:/#" \
    -e "s#\(url \|path \|code \)/c/#\1C:/#" \
    -e "s#(cwd /c/#(cwd C:/#" \
    -e "s#^\(  line:   - \[ \] \)[0-9][0-9]:[0-9][0-9]#\1HH:MM#" \
    -e "s#/c/Users/#C:/Users/#g"
}

check() {
  local desc="$1"
  shift
  local out_bash out_pwsh rc_bash rc_pwsh
  out_bash="$(bash bin/cli --dry-run "$@" 2>&1 | normalise)"
  rc_bash=$?
  out_pwsh="$("$PWSH" -NoProfile -File bin/cli.ps1 --dry-run "$@" 2>&1 | normalise)"
  rc_pwsh=$?
  CHECKED=$((CHECKED + 1))
  if [ "$out_bash" != "$out_pwsh" ] || [ "$rc_bash" != "$rc_pwsh" ]; then
    FAILED=$((FAILED + 1))
    echo "MISMATCH: cli $*  ($desc)"
    diff <(echo "$out_bash") <(echo "$out_pwsh") | sed 's/^/    /'
  fi
}

echo "checking links..."
while read -r key; do check link link "$key"; done < <(jq -r '.links | keys[]' "$CONFIG")

echo "checking folders..."
while read -r key; do check folder folder "$key"; done < <(jq -r '.folders | keys[]' "$CONFIG")

echo "checking searches..."
while read -r key; do check search search "$key" test query; done < <(jq -r '.searches | keys[]' "$CONFIG")
check "search default" search test query

echo "checking captures..."
while read -r key; do check capture "$key" a test line; done < <(jq -r '.captures | keys[]' "$CONFIG")

echo "checking code, clone, set, rm..."
check code code automation_engine
check clone clone modelOS
check set set link test-key https://example.com
check set-folder set folder test-key "\${PROTOCOL}/x"
check rm rm link pkm-ticktick

echo "checking errors and help..."
check "no args"
check "help" --help
check "bad verb" nonsense
check "bad link" link nope
check "bare link" link
check "bare folder" folder
check "bare search" search
check "verb help" link --help
check "bad table" set nope key value
check "rm missing" rm link nope

echo
echo "$CHECKED commands checked, $FAILED mismatches"
[ "$FAILED" -eq 0 ]
