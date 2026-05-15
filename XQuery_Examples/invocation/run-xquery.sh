#!/usr/bin/env bash
# Run an XQuery against a FundsXML document via Saxon-HE (CLI).
#
# Usage: run-xquery.sh <query.xq> <input.xml> [output] [name=value ...]
# Exit:  0 on success, 2 setup error, Saxon's code otherwise.
#
# Saxon's net.sf.saxon.Query takes external variables as bare `name=value`
# arguments (NOT `-param:` — that is the XSLT entry point; and a leading `!`
# would set serialization params instead). tools/fetch-tools.sh provides
# Saxon-HE in .lib/.
set -euo pipefail

Q="${1:?usage: run-xquery.sh <query.xq> <input.xml> [output] [name=value ...]}"
IN="${2:?input xml required}"
OUT="${3:-}"
shift 2 || true
[[ $# -ge 1 && "${1:-}" != *=* ]] && { OUT="$1"; shift; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB="${REPO_ROOT}/.lib"
if [[ ! -f "${LIB}/Saxon-HE-12.5.jar" ]]; then
  echo "Saxon not present; fetching..." >&2
  "${REPO_ROOT}/tools/fetch-tools.sh" >/dev/null
fi
SCP="${LIB}/Saxon-HE-12.5.jar:${LIB}/xmlresolver-5.2.2.jar:${LIB}/xmlresolver-5.2.2-data.jar"

if [[ -n "$OUT" ]]; then
  java -cp "$SCP" net.sf.saxon.Query -q:"$Q" -s:"$IN" -o:"$OUT" "$@"
  echo "wrote $OUT"
else
  java -cp "$SCP" net.sf.saxon.Query -q:"$Q" -s:"$IN" "$@"
fi
