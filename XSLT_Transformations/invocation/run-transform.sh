#!/usr/bin/env bash
# Run any XSLT 2.0 stylesheet in this repo via Saxon-HE (CLI).
#
# Usage: run-transform.sh <stylesheet.xslt> <input.xml> <output> [name=value ...]
# Exit:  0 on success, 2 on setup error, Saxon's code otherwise.
#
# The Custom_Internal_Checks / Factsheet / CSV stylesheets are XSLT 2.0, so an
# XSLT 2.0/3.0 engine (Saxon) is required — xsltproc/lxml (XSLT 1.0) will not
# work. tools/fetch-tools.sh provides Saxon-HE in .lib/.
set -euo pipefail

XSL="${1:?usage: run-transform.sh <stylesheet> <input.xml> <output> [params...]}"
IN="${2:?input xml required}"
OUT="${3:?output path required}"
shift 3 || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB="${REPO_ROOT}/.lib"
if [[ ! -f "${LIB}/Saxon-HE-12.5.jar" ]]; then
  echo "Saxon not present; fetching..." >&2
  "${REPO_ROOT}/tools/fetch-tools.sh" >/dev/null
fi

# Saxon 12.x needs xmlresolver on the classpath (CatalogResourceResolver).
SCP="${LIB}/Saxon-HE-12.5.jar:${LIB}/xmlresolver-5.2.2.jar:${LIB}/xmlresolver-5.2.2-data.jar"

java -cp "$SCP" net.sf.saxon.Transform \
     -s:"$IN" -xsl:"$XSL" -o:"$OUT" "$@"
echo "wrote $OUT"
