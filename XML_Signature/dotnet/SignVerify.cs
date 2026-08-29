// Enveloped XML-DSig sign / verify in .NET via System.Security.Cryptography.Xml.
//
//   dotnet run --project XML_Signature/dotnet -- sign   in.xml  out.xml
//   dotnet run --project XML_Signature/dotnet -- verify signed.xml [cert.pem]
// Exit: 0 ok, 1 invalid, 2 setup error.
//
// Verified with .NET SDK 8: signs, verifies, detects tampering, and
// cross-verifies with the Java (Santuario) output in both directions.
// Same profile as the Apache Santuario (Java) example: RSA-SHA256, exclusive
// C14N, enveloped, signer cert embedded in KeyInfo, so files cross-verify.
// Keys: the Java GenerateTestKey (./mvnw -pl XML_Signature/java compile
// exec:java -Dexec.mainClass=GenerateTestKey) writes the PKCS#12
// test-signing.p12 used here.

using System;
using System.IO;
using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography.Xml;
using System.Xml;

internal static class SignVerify
{
    private static int Main(string[] args)
    {
        if (args.Length < 2) { Console.Error.WriteLine("usage: sign|verify ..."); return 2; }
        string keysDir = Path.Combine(AppContext.BaseDirectory,
            "..", "..", "..", "..", "keys");

        var doc = new XmlDocument { PreserveWhitespace = true };
        // XXE-hardened load.
        using (var r = XmlReader.Create(args[1],
                   new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit,
                                           XmlResolver = null }))
            doc.Load(r);

        if (args[0] == "sign")
        {
            var cert = new X509Certificate2(
                Path.Combine(keysDir, "test-signing.p12"), "changeit",
                X509KeyStorageFlags.Exportable);
            var rsa = cert.GetRSAPrivateKey();

            var signedXml = new SignedXml(doc) { SigningKey = rsa };
            signedXml.SignedInfo.CanonicalizationMethod =
                SignedXml.XmlDsigExcC14NTransformUrl;
            signedXml.SignedInfo.SignatureMethod =
                "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256";

            var reference = new Reference("");
            reference.DigestMethod = "http://www.w3.org/2001/04/xmlenc#sha256";
            reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());
            reference.AddTransform(new XmlDsigExcC14NTransform());
            signedXml.AddReference(reference);

            var ki = new KeyInfo();
            ki.AddClause(new KeyInfoX509Data(cert));
            signedXml.KeyInfo = ki;

            signedXml.ComputeSignature();
            // ds:Signature must be the LAST child of <FundsXML4>.
            doc.DocumentElement!.AppendChild(
                doc.ImportNode(signedXml.GetXml(), true));
            doc.Save(args[2]);
            Console.WriteLine($"signed -> {args[2]}");
            return 0;
        }

        if (args[0] == "verify")
        {
            var signedXml = new SignedXml(doc);
            var sig = (XmlElement)doc.GetElementsByTagName(
                "Signature", SignedXml.XmlDsigNamespaceUrl)[0]!;
            signedXml.LoadXml(sig);

            bool ok;
            if (args.Length >= 3)
            {
                var pinned = new X509Certificate2(args[2]);
                ok = signedXml.CheckSignature(pinned, true);
                Console.WriteLine($"pinned cert: {pinned.Subject}");
            }
            else
            {
                ok = signedXml.CheckSignature(); // trusts embedded key (demo)
            }
            Console.WriteLine(ok ? "VALID: signature OK"
                                 : "INVALID: signature check failed");
            return ok ? 0 : 1;
        }

        Console.Error.WriteLine($"unknown mode {args[0]}");
        return 2;
    }
}
