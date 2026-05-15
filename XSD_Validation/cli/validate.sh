#!/usr/bin/env bash
# XSD validation via the command line (xmllint).
#
# Usage: XSD_Validation/cli/validate.sh <version> <xml-file>
# Exit:  0 = valid, 1 = invalid, 2 = usage/setup error
#
# Validates against the official released schema, materialized locally by
# tools/fetch-schema.sh (handles the GitHub 302 redirect and the relative
# xmldsig-core-schema.xsd import that FundsXML 4.2.9+ requires).
set -euo pipefail

VERSION="${1:?usage: validate.sh <version> <xml-file>}"
XML="${2:?usage: validate.sh <version> <xml-file>}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA="${REPO_ROOT}/.schema-cache/${VERSION}/FundsXML.xsd"

if [[ ! -f "$SCHEMA" ]]; then
  echo "schema not cached; fetching official release ${VERSION}..." >&2
  "${REPO_ROOT}/tools/fetch-schema.sh" "$VERSION" >/dev/null
fi

# --nonet: never hit the network during validation (XXE / entity hardening).
#          The schema was already fetched explicitly above.
if xmllint --noout --nonet --schema "$SCHEMA" "$XML" 2>/tmp/xmllint.$$; then
  echo "VALID: $XML (FundsXML $VERSION)"
  rm -f /tmp/xmllint.$$
  exit 0
else
  echo "INVALID: $XML (FundsXML $VERSION)" >&2
  cat /tmp/xmllint.$$ >&2
  rm -f /tmp/xmllint.$$
  exit 1
fi

# --- Alternative: Saxon (XSD 1.1, follows HTTP redirects natively) ----------
# Saxon-EE/HE can validate and DOES follow the 302, but the relative
# xmldsig-core-schema.xsd import still needs both files side by side, so the
# fetched local copy is used here too:
#   java -cp saxon-he.jar com.saxonica.Validate \
#        -xsd:"$SCHEMA" -s:"$XML"
