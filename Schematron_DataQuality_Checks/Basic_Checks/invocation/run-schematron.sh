#!/usr/bin/env bash
# Schematron validation via the command line (SchXslt + Saxon).
#
# Usage: run-schematron.sh <xml-file> [--fail-on error|any]
# Exit:  0 = pass, 1 = fail (per --fail-on), 2 = setup error
#
# basic_checks.sch uses queryBinding="xslt2", so an XSLT 2.0 processor (Saxon)
# is required. SchXslt compiles the Schematron to XSLT and applies it, emitting
# an SVRL report which svrl-summary.py then classifies.
set -euo pipefail

XML="${1:?usage: run-schematron.sh <xml-file> [--fail-on error|any]}"
shift || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCH="${REPO_ROOT}/Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch"
LIB="${REPO_ROOT}/.lib"

if [[ ! -f "${LIB}/schxslt-cli-1.10.1.jar" ]]; then
  echo "Java toolchain not present; fetching (Saxon + SchXslt)..." >&2
  "${REPO_ROOT}/tools/fetch-tools.sh" >/dev/null
fi

# SchXslt-only classpath. The CLI jar bundles its own Saxon; do NOT add the
# standalone Saxon-HE jar here (different org.xmlresolver API → breakage).
CP="${LIB}/schxslt-cli-1.10.1.jar:${LIB}/commons-cli-1.5.0.jar:${LIB}/slf4j-api-1.7.32.jar:${LIB}/slf4j-nop-1.7.32.jar"
SVRL="$(mktemp)"
trap 'rm -f "$SVRL"' EXIT

java -cp "$CP" name.dmaus.schxslt.cli.Application \
     -s "$SCH" -d "$XML" -o "$SVRL" >/dev/null 2>&1 || true

python3 "${REPO_ROOT}/Schematron_DataQuality_Checks/Basic_Checks/invocation/svrl-summary.py" \
        "$SVRL" "$@"
