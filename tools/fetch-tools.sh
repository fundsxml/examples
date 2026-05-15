#!/usr/bin/env bash
# fetch-tools.sh — Fetch the Java XML toolchain jars used by the examples.
#
# Why: this repo's Schematron uses queryBinding="xslt2" and the Basic/Custom
# XSLT reports are XSLT 2.0 — both need a Saxon (XSLT 2.0/3.0) processor, which
# is not part of a base OS install. SchXslt compiles ISO Schematron to XSLT.
#
# Two independent classpaths are produced, on purpose:
#   * SAXON_CP   — Saxon-HE + xmlresolver, for XSLT 2.0 transforms.
#   * SCHXSLT_CP — the SchXslt CLI (a self-contained jar that already bundles
#                  its own Saxon) + commons-cli + slf4j. Mixing the standalone
#                  Saxon-HE-12.5 into this classpath breaks SchXslt: the two
#                  Saxons need different org.xmlresolver APIs.
#
# All jars come from Maven Central (curl honours https_proxy / HTTPS_PROXY for
# locked-down enterprise networks). Jars land in .lib/ (gitignored) — they are
# external dependencies, not repo source.
#
# Usage:  tools/fetch-tools.sh
# Output: SAXON_CP=... and SCHXSLT_CP=... (consumed by the invocation scripts).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="${REPO_ROOT}/.lib"
mkdir -p "$LIB"
M2="https://repo1.maven.org/maven2"

fetch() {
  local url="$1" out="$2"
  if [[ -s "$out" ]]; then echo "cached: $out" >&2; return 0; fi
  echo "fetch:  $url" >&2
  curl -sSL --fail -m 120 "$url" -o "$out"
}

# --- Saxon-HE (XSLT 2.0/3.0) -------------------------------------------------
fetch "${M2}/net/sf/saxon/Saxon-HE/12.5/Saxon-HE-12.5.jar"                 "${LIB}/Saxon-HE-12.5.jar"
# Saxon 12.x requires org.xmlresolver at runtime (CatalogResourceResolver).
fetch "${M2}/org/xmlresolver/xmlresolver/5.2.2/xmlresolver-5.2.2.jar"      "${LIB}/xmlresolver-5.2.2.jar"
fetch "${M2}/org/xmlresolver/xmlresolver/5.2.2/xmlresolver-5.2.2-data.jar" "${LIB}/xmlresolver-5.2.2-data.jar"

# --- SchXslt CLI (self-contained: bundles its own Saxon + XSLT) --------------
fetch "${M2}/name/dmaus/schxslt/cli/1.10.1/cli-1.10.1.jar"   "${LIB}/schxslt-cli-1.10.1.jar"
fetch "${M2}/commons-cli/commons-cli/1.5.0/commons-cli-1.5.0.jar" "${LIB}/commons-cli-1.5.0.jar"
fetch "${M2}/org/slf4j/slf4j-api/1.7.32/slf4j-api-1.7.32.jar"     "${LIB}/slf4j-api-1.7.32.jar"
fetch "${M2}/org/slf4j/slf4j-nop/1.7.32/slf4j-nop-1.7.32.jar"     "${LIB}/slf4j-nop-1.7.32.jar"

echo "SAXON_CP=${LIB}/Saxon-HE-12.5.jar:${LIB}/xmlresolver-5.2.2.jar:${LIB}/xmlresolver-5.2.2-data.jar"
echo "SCHXSLT_CP=${LIB}/schxslt-cli-1.10.1.jar:${LIB}/commons-cli-1.5.0.jar:${LIB}/slf4j-api-1.7.32.jar:${LIB}/slf4j-nop-1.7.32.jar"
