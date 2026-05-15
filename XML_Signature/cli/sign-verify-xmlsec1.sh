#!/usr/bin/env bash
# Enveloped XML-DSig sign / verify on the command line with xmlsec1
# (the xmlsec C library CLI, package: libxmlsec1 / xmlsec1).
#
#   sign-verify-xmlsec1.sh sign   <in.xml>  <out.xml>
#   sign-verify-xmlsec1.sh verify <signed.xml> [cert.pem]
#
# Reference implementation (xmlsec1 not installed in the dev environment:
#   Debian/Ubuntu: sudo apt-get install xmlsec1
#   macOS:         brew install xmlsec1
#
# Unlike the Java/Python examples, xmlsec1 signs an EXISTING <ds:Signature>
# template in the document — so it pairs naturally with the committed
# FundsXML_Files/4.2.9/signed/Signed_Fund_Skeleton.xml (which already carries a
# placeholder ds:Signature). Keys: XML_Signature/generate-test-key.sh.
set -euo pipefail

MODE="${1:?usage: sign-verify-xmlsec1.sh sign|verify ...}"
KEYS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/keys"

case "$MODE" in
  sign)
    IN="${2:?in.xml}"; OUT="${3:?out.xml}"
    # The template's ds:Signature/SignedInfo must already exist (it does in the
    # signed skeleton). xmlsec1 fills DigestValue + SignatureValue + KeyInfo.
    xmlsec1 --sign \
      --privkey-pem "${KEYS}/test-signing-key.pem,${KEYS}/test-signing-cert.pem" \
      --output "$OUT" "$IN"
    echo "signed -> $OUT"
    ;;
  verify)
    SIGNED="${2:?signed.xml}"
    CERT="${3:-${KEYS}/test-signing-cert.pem}"
    # --trusted-pem pins the signer cert (do NOT trust only the embedded key).
    xmlsec1 --verify --trusted-pem "$CERT" "$SIGNED" \
      && echo "VALID: signature OK" \
      || { echo "INVALID: signature check failed"; exit 1; }
    ;;
  *)
    echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
