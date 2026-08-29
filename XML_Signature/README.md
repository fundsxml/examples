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
./mvnw -q -pl XML_Signature/java compile exec:java -Dexec.mainClass=GenerateTestKey
# -> XML_Signature/keys/ (gitignored).  Windows: use mvnw.cmd
```
`GenerateTestKey` uses the JDK's own `keytool` (no openssl, so it works on
Windows too) to write a throwaway self-signed RSA-2048 keystore
`test-signing.p12` (alias `fundsxml`, pass `changeit`) and the PEM certificate
`test-signing-cert.pem`. **Demo only — never commit private keys.**

## Stacks

| Stack | Entry point | Status |
|-------|-------------|--------|
| Java — Apache Santuario | [`java/SignFundsXml.java`](java/SignFundsXml.java) / [`java/VerifyFundsXml.java`](java/VerifyFundsXml.java) | ✅ verified (sign, verify, tamper-detect) |
| CLI — `xmlsec1` | [`cli/sign-verify-xmlsec1.sh`](cli/sign-verify-xmlsec1.sh) | reference (needs `xmlsec1`) |
| Python — `signxml` | [`python/sign_verify_signxml.py`](python/sign_verify_signxml.py) | reference (`pip install -e ".[signature]"` adds `signxml`) |
| .NET — `SignedXml` | [`dotnet/SignVerify.cs`](dotnet/SignVerify.cs) | verified (.NET SDK 8): sign, verify, tamper; cross-verifies with Java both ways |

## Run (Java / Apache Santuario — verified)

Standalone & cross-platform via the committed Maven Wrapper (`./mvnw`, or
`mvnw.cmd` on Windows), from the repo root — xmlsec comes from Maven Central:

```bash
M="./mvnw -q -pl XML_Signature/java compile exec:java"

# one-off: throwaway key (JDK keytool, no openssl)
$M -Dexec.mainClass=GenerateTestKey

# sign
$M -Dexec.mainClass=SignFundsXml \
   -Dexec.args="FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml signed.xml \
                XML_Signature/keys/test-signing.p12 changeit fundsxml"

# verify — pin the signer cert (don't trust only the embedded key)
$M -Dexec.mainClass=VerifyFundsXml \
   -Dexec.args="signed.xml XML_Signature/keys/test-signing-cert.pem"
```

`VerifyFundsXml` exits 0 on a valid signature, 1 on tamper/failure (verified:
flipping one digit in a signed file → `INVALID`). Santuario verification runs
with **secure validation** enabled.

> **Note on `xmlsec1`:** it signs an *existing* `ds:Signature` template, so it
> pairs naturally with the committed signed skeleton; the Java/.NET/Python
> examples instead build and append the `ds:Signature` themselves. Because
> the skeleton's template uses **inclusive** C14N (`REC-xml-c14n-20010315`),
> only the enveloped transform and a `ds:KeyName` in `KeyInfo`, the xmlsec1
> output does **not** follow the exclusive-C14N / embedded-X509 profile above:
> Java and .NET can still verify it against the pinned certificate, but not
> from the embedded `KeyInfo` (which carries no key).

A real signed file is **not committed** — the signature is bound to the
throwaway key, which is regenerated per run. CI signs → verifies as a roundtrip.
