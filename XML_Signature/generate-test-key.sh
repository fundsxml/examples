#!/usr/bin/env bash
# generate-test-key.sh — create a THROWAWAY self-signed RSA key + cert for the
# XML-signature examples.
#
# Output (into XML_Signature/keys/, gitignored — never commit private keys):
#   test-signing.p12        PKCS#12 keystore  (alias: fundsxml, pass: changeit)
#   test-signing-cert.pem   public certificate (for verification / xmlsec1)
#   test-signing-key.pem    private key in PEM (for xmlsec1 / signxml)
#
# FOR DEMO USE ONLY — 2048-bit, 10-year self-signed, hard-coded password.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/keys"
mkdir -p "$DIR"
PASS="changeit"

openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
  -keyout "$DIR/test-signing-key.pem" \
  -out    "$DIR/test-signing-cert.pem" \
  -subj "/C=AT/O=FundsXML Examples/OU=Demo/CN=fundsxml-test-signer" 2>/dev/null

openssl pkcs12 -export \
  -inkey "$DIR/test-signing-key.pem" \
  -in    "$DIR/test-signing-cert.pem" \
  -name  fundsxml \
  -out   "$DIR/test-signing.p12" \
  -passout "pass:${PASS}"

echo "wrote: $DIR/test-signing.p12 (alias=fundsxml pass=${PASS})"
echo "       $DIR/test-signing-cert.pem  $DIR/test-signing-key.pem"
