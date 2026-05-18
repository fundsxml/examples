#!/bin/sh
# XSD validation from the command line with xmllint (Linux/macOS).
#
# Usage: XSD_Validation/cli/validate.sh <schema> <xml-file>
# Exit:  0 = valid, 1 = invalid, 2 = usage/setup error
#
# You give it exactly two things: the schema and the instance document.
# <schema> is a path to an XSD file OR a remote URL, e.g. the official
# release: https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
# No version, no env var, no cache — whatever you point at is used as-is.
#
# xmllint validates the instance with --nonet (XXE / external-entity
# hardening). To keep that hardening while still accepting a *remote* schema,
# a URL schema (and, when it imports it, the relative xmldsig-core-schema.xsd
# sibling that FundsXML 4.2.9+ needs) is fetched into a temp dir first, then
# validation runs offline against that local copy. A local schema path is
# passed straight through (its xmldsig sibling, if imported, must sit next
# to it — as it does in any complete copy of an official release).
#
# POSIX sh (no bash-isms) so it runs under dash/ash too. The Windows
# counterpart is validate.ps1 in this directory.

set -eu

SCHEMA="${1:-}"
XML="${2:-}"
if [ -z "$SCHEMA" ] || [ -z "$XML" ]; then
  echo "usage: validate.sh <schema> <xml-file>" >&2
  exit 2
fi

TMP=
trap 'rm -f "${ERR:-}"; [ -n "$TMP" ] && rm -rf "$TMP"' EXIT

case "$SCHEMA" in
  http://*|https://*)
    # Remote schema: materialise it (and the xmldsig sibling it may import)
    # into a temp dir so the instance can still be validated with --nonet.
    TMP=$(mktemp -d)
    LOCAL="$TMP/FundsXML.xsd"
    echo "schema: fetch $SCHEMA" >&2
    curl -sSL --fail -m 60 "$SCHEMA" -o "$LOCAL"
    if grep -q 'xmldsig-core-schema\.xsd' "$LOCAL"; then
      SIB_URL="${SCHEMA%/*}/xmldsig-core-schema.xsd"
      echo "schema: fetch $SIB_URL" >&2
      curl -sSL --fail -m 60 "$SIB_URL" -o "$TMP/xmldsig-core-schema.xsd"
    fi
    SCHEMA="$LOCAL"
    ;;
esac

# --nonet: never hit the network during validation (XXE / entity hardening).
ERR=$(mktemp)
if xmllint --noout --nonet --schema "$SCHEMA" "$XML" 2>"$ERR"; then
  echo "VALID: $XML (schema $1)"
  exit 0
else
  echo "INVALID: $XML (schema $1)" >&2
  cat "$ERR" >&2
  exit 1
fi
