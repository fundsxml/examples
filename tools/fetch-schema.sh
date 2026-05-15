#!/usr/bin/env bash
# fetch-schema.sh — Fetch the official FundsXML XSD release from GitHub.
#
# WHY THIS SCRIPT EXISTS
# ----------------------
# Validation is done against the canonical schema URL:
#
#   https://github.com/fundsxml/schema/releases/download/<version>/FundsXML.xsd
#
# That URL returns HTTP 302 to objects.githubusercontent.com. Processors with a
# simple HTTP client (e.g. libxml2 / xmllint) do NOT follow redirects and fail.
# In addition, from release 4.2.9 onward `FundsXML.xsd` imports
# `xmldsig-core-schema.xsd` via a RELATIVE path — both files must therefore sit
# in the same directory, otherwise XSD compilation fails
# ("{http://www.w3.org/2000/09/xmldsig#}Signature does not resolve").
#
# Enterprise reality: on locked-down networks the download goes through an HTTP
# proxy (curl honours https_proxy / HTTPS_PROXY). No hand-maintained XML catalog
# is used — the source of truth stays the official release.
#
# Usage:
#   tools/fetch-schema.sh <version> [target-dir]
#   tools/fetch-schema.sh 4.2.9
#   tools/fetch-schema.sh 4.1.0 /tmp/xsd
#
# Output: path to the local FundsXML.xsd on stdout (usable by scripts).
set -euo pipefail

VERSION="${1:?Usage: fetch-schema.sh <version> [target-dir]}"
TARGET="${2:-.schema-cache/${VERSION}}"
BASE="https://github.com/fundsxml/schema/releases/download/${VERSION}"

mkdir -p "$TARGET"

fetch() {
  local name="$1"
  local out="${TARGET}/${name}"
  if [[ -s "$out" ]]; then
    echo "cached: $out" >&2
    return 0
  fi
  echo "fetch:  ${BASE}/${name} -> $out" >&2
  # -L follows the GitHub redirect; --fail aborts on HTTP error.
  curl -sSL --fail -m 60 "${BASE}/${name}" -o "$out"
}

fetch "FundsXML.xsd"

# From 4.2.9 on, FundsXML.xsd imports xmldsig-core-schema.xsd via a relative
# path — without that file the schema does not compile
# ("{http://www.w3.org/2000/09/xmldsig#}Signature does not resolve").
# Older releases (4.1.0, 4.0.0) are self-contained and do not reference it.
# Fetch the sibling only when it is actually imported.
if grep -q 'xmldsig-core-schema\.xsd' "${TARGET}/FundsXML.xsd"; then
  fetch "xmldsig-core-schema.xsd"
fi

echo "${TARGET}/FundsXML.xsd"
