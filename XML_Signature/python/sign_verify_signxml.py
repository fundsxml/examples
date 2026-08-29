#!/usr/bin/env python3
"""Enveloped XML-DSig sign / verify in Python via `signxml`.

Usage:
  python sign_verify_signxml.py sign   <in.xml>  <out.xml>
  python sign_verify_signxml.py verify <signed.xml> [cert.pem]

Exit: 0 ok, 1 invalid signature, 2 setup error.

Reference implementation (signxml not installed in the dev environment):
  pip install signxml
Keys: the Java GenerateTestKey (./mvnw -pl XML_Signature/java compile
exec:java -Dexec.mainClass=GenerateTestKey) writes test-signing.p12,
test-signing-cert.pem and the PKCS#8 private key test-signing-key.pem (the
one this script needs) to XML_Signature/keys/. signxml is an optional extra
of the repo's pyproject.toml: pip install -e ".[signature]".
RSA-SHA256, exclusive C14N, enveloped — same profile as the Apache Santuario
(Java) example, so files cross-verify between stacks.
"""
import sys
from pathlib import Path

KEYS = Path(__file__).resolve().parents[1] / "keys"


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    mode = sys.argv[1]

    try:
        from lxml import etree
        from signxml import XMLSigner, XMLVerifier, methods
    except ImportError:
        print("signxml not installed. Run: pip install signxml",
              file=sys.stderr)
        return 2

    if mode == "sign":
        src, out = sys.argv[2], sys.argv[3]
        data = etree.parse(src).getroot()
        key = (KEYS / "test-signing-key.pem").read_bytes()
        cert = (KEYS / "test-signing-cert.pem").read_bytes()
        signed = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
        ).sign(data, key=key, cert=cert)
        Path(out).write_bytes(etree.tostring(signed))
        print(f"signed -> {out}")
        return 0

    if mode == "verify":
        signed = etree.parse(sys.argv[2]).getroot()
        try:
            if len(sys.argv) >= 4:
                XMLVerifier().verify(
                    signed, x509_cert=Path(sys.argv[3]).read_text())
            else:
                # Trust the embedded cert ONLY for the demo; in production pin
                # x509_cert / ca_pem_file to a known signer.
                XMLVerifier().verify(signed)
            print("VALID: signature OK")
            return 0
        except Exception as e:  # signxml raises on any failure
            print(f"INVALID: {e}")
            return 1

    print(f"unknown mode {mode!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
