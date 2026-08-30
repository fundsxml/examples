#!/bin/sh
# Enveloped XML-DSig sign / verify on the command line with xmlsec1
# (the xmlsec C library CLI; package: libxmlsec1 / xmlsec1).
#
#   sign-verify-xmlsec1.sh sign   <in.xml>  <out.xml>
#   sign-verify-xmlsec1.sh verify <signed.xml> [cert.pem]
#
# xmlsec1 is a native CLI tool (not bundled):
#   Debian/Ubuntu: sudo apt-get install xmlsec1
#   macOS:         brew install xmlsec1
# Verified (xmlsec1 1.2.33, also in CI): sign -> verify, tamper detected, and
# the output cross-verifies with the Java (Santuario) and .NET (SignedXml)
# verifiers, both pinned and from the embedded certificate; xmlsec1 in turn
# verifies files signed by Java and .NET.
#
# Keys: generated cross-platform by the Java GenerateTestKey (no openssl):
#   ./mvnw -q -pl XML_Signature/java compile exec:java -Dexec.mainClass=GenerateTestKey
# It writes test-signing.p12, test-signing-cert.pem AND test-signing-key.pem
# (PKCS#8) into XML_Signature/keys/ — the last two are what xmlsec1 needs.
#
# Unlike the Java/.NET/Python examples, xmlsec1 signs an EXISTING <ds:Signature>
# template in the document. The committed
# FundsXML_Files/4.2.9/signed/Signed_Fund_Skeleton.xml is exactly that
# template, already in the shared profile: SignedInfo with exclusive C14N,
# enveloped + exclusive-C14N transforms, RSA-SHA256 / SHA-256, and an empty
# <ds:X509Certificate/> that xmlsec1 fills with the signer cert (that is why
# --privkey-pem gets "key,cert"). To sign any other FundsXML file, append that
# ds:Signature block as the last child of <FundsXML4> first.
#
# POSIX sh; the Windows counterpart is sign-verify.ps1 in this directory.

set -eu

MODE="${1:-}"
if [ -z "$MODE" ]; then
  echo "usage: sign-verify-xmlsec1.sh sign|verify ..." >&2
  exit 2
fi
KEYS=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)/keys

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
    if xmlsec1 --verify --trusted-pem "$CERT" "$SIGNED"; then
      echo "VALID: signature OK"
    else
      echo "INVALID: signature check failed" >&2
      exit 1
    fi
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 2
    ;;
esac
