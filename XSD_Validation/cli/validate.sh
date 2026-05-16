#!/bin/sh
# XSD validation from the command line with xmllint (Linux/macOS).
#
# Usage: XSD_Validation/cli/validate.sh <version> <xml-file>
# Exit:  0 = valid, 1 = invalid, 2 = usage/setup error
#
# Standalone: this script resolves the official schema itself — no prior tool
# step. Same 3-step convention as every other stack:
#   1. $FUNDSXML_SCHEMA_DIR  — a dir with FundsXML.xsd (+ xmldsig sibling for
#      4.2.9+). Used as-is, NO network (offline / corporate-network escape).
#   2. .schema-cache/<version>/FundsXML.xsd  — reused if present.
#   3. download from the official GitHub release (curl -L follows the 302),
#      caching into .schema-cache/; the relative xmldsig-core-schema.xsd
#      sibling is fetched only when FundsXML.xsd imports it (4.2.9+).
#
# POSIX sh (no bash-isms) so it runs under dash/ash too. The Windows
# counterpart is validate.ps1 in this directory.

set -eu

VERSION="${1:-}"
XML="${2:-}"
if [ -z "$VERSION" ] || [ -z "$XML" ]; then
  echo "usage: validate.sh <version> <xml-file>" >&2
  exit 2
fi

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BASE="https://github.com/fundsxml/schema/releases/download/${VERSION}"

fetch() {  # url dest
  echo "schema: fetch $1" >&2
  curl -sSL --fail -m 60 "$1" -o "$2"
}

if [ -n "${FUNDSXML_SCHEMA_DIR:-}" ]; then
  SCHEMA="${FUNDSXML_SCHEMA_DIR}/FundsXML.xsd"
  if [ ! -f "$SCHEMA" ]; then
    echo "FUNDSXML_SCHEMA_DIR set but $SCHEMA not found" >&2
    exit 2
  fi
  echo "schema: using \$FUNDSXML_SCHEMA_DIR -> $SCHEMA" >&2
else
  CACHE_DIR="${REPO_ROOT}/.schema-cache/${VERSION}"
  SCHEMA="${CACHE_DIR}/FundsXML.xsd"
  if [ -f "$SCHEMA" ]; then
    echo "schema: cached -> $SCHEMA" >&2
  else
    mkdir -p "$CACHE_DIR"
    fetch "${BASE}/FundsXML.xsd" "$SCHEMA"
    if grep -q 'xmldsig-core-schema\.xsd' "$SCHEMA"; then
      fetch "${BASE}/xmldsig-core-schema.xsd" \
            "${CACHE_DIR}/xmldsig-core-schema.xsd"
    fi
  fi
fi

# --nonet: never hit the network during validation (XXE / entity hardening);
# the schema was already materialised above.
ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT
if xmllint --noout --nonet --schema "$SCHEMA" "$XML" 2>"$ERR"; then
  echo "VALID: $XML (FundsXML $VERSION)"
  exit 0
else
  echo "INVALID: $XML (FundsXML $VERSION)" >&2
  cat "$ERR" >&2
  exit 1
fi
