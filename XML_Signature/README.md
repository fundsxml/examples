# XML Signature (XML-DSig)

![status](https://img.shields.io/badge/Java%20(Santuario)-verified-brightgreen) ![profile](https://img.shields.io/badge/RSA--SHA256%20%2F%20exc--C14N%20%2F%20enveloped-blue)

Sign and verify FundsXML with **enveloped XML Digital Signatures**. All stacks
use the same profile so signed files **cross-verify** between them:

| Property | Value |
|----------|-------|
| Signature method | RSA-SHA256 |
| Digest | SHA-256 |
| Canonicalization | Exclusive C14N (`xml-exc-c14n#`) |
| Transform | enveloped-signature + exclusive C14N |
| Reference | `URI=""` (whole document) |
| KeyInfo | signer X.509 certificate embedded |
| Placement | `ds:Signature` is the **last child of `<FundsXML4>`** — exactly where the 4.2.9 schema allows it (`xmldsig-core-schema.xsd` import) |

A signed file **stays XSD-valid** (verified) and matches the structure of the
committed [`FundsXML_Files/4.2.9/signed/Signed_Fund_Skeleton.xml`](../FundsXML_Files/4.2.9/signed/)
placeholder.

## Keys

```bash
XML_Signature/generate-test-key.sh   # -> XML_Signature/keys/ (gitignored)
```
Throwaway self-signed RSA-2048 (`test-signing.p12` alias `fundsxml`, pass
`changeit`; plus PEM key/cert). **Demo only — never commit private keys.**

## Stacks

| Stack | Entry point | Status |
|-------|-------------|--------|
| Java — Apache Santuario | [`java/SignFundsXml.java`](java/SignFundsXml.java) / [`java/VerifyFundsXml.java`](java/VerifyFundsXml.java) | ✅ verified (sign, verify, tamper-detect) |
| CLI — `xmlsec1` | [`cli/sign-verify-xmlsec1.sh`](cli/sign-verify-xmlsec1.sh) | reference (needs `xmlsec1`) |
| Python — `signxml` | [`python/sign_verify_signxml.py`](python/sign_verify_signxml.py) | reference (`pip install signxml`) |
| .NET — `SignedXml` | [`dotnet/SignVerify.cs`](dotnet/SignVerify.cs) | reference (needs .NET SDK) |

## Run (Java / Apache Santuario — verified)

```bash
tools/fetch-tools.sh
XML_Signature/generate-test-key.sh
CP=.lib/xmlsec-4.0.4.jar:.lib/commons-codec-1.18.0.jar:.lib/slf4j-api-2.0.17.jar:.lib/slf4j-nop-2.0.17.jar
javac -cp "$CP" -d /tmp/sig XML_Signature/java/SignFundsXml.java XML_Signature/java/VerifyFundsXml.java

# sign
java -cp "$CP:/tmp/sig" SignFundsXml \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml signed.xml \
  XML_Signature/keys/test-signing.p12 changeit fundsxml

# verify — pin the signer cert (don't trust only the embedded key)
java -cp "$CP:/tmp/sig" VerifyFundsXml signed.xml XML_Signature/keys/test-signing-cert.pem
```

`VerifyFundsXml` exits 0 on a valid signature, 1 on tamper/failure (verified:
flipping one digit in a signed file → `INVALID`). Santuario verification runs
with **secure validation** enabled.

> **Note on `xmlsec1`:** it signs an *existing* `ds:Signature` template, so it
> pairs naturally with the committed signed skeleton; the Java/.NET/Python
> examples instead build and append the `ds:Signature` themselves.

A real signed file is **not committed** — the signature is bound to the
throwaway key, which is regenerated per run. CI signs → verifies as a roundtrip.
