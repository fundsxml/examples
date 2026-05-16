// VerifyFundsXml — verify an enveloped XML-DSig signature with Apache Santuario.
//
// Run from the repo root with the Maven Wrapper:
//   ./mvnw -q -pl XML_Signature/java exec:java -Dexec.mainClass=VerifyFundsXml \
//       -Dexec.args="<signed.xml> [cert.pem]"
//
// With no cert argument the certificate embedded in KeyInfo/X509Data is used
// (self-verifiable file). Pass a PEM cert to pin verification to a known key
// (recommended in production — never trust the key shipped inside the document
// alone). Exit: 0 = signature valid, 1 = invalid, 2 = setup error.
//
// Security: namespace-aware, XXE-hardened parser; "secure validation" mode on.

import java.io.FileInputStream;
import java.security.PublicKey;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import javax.xml.parsers.DocumentBuilderFactory;
import org.apache.xml.security.Init;
import org.apache.xml.security.signature.XMLSignature;
import org.apache.xml.security.utils.Constants;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

public class VerifyFundsXml {
    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("usage: VerifyFundsXml <signed.xml> [cert.pem]");
            System.exit(2);
        }
        Init.init();

        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        Document doc;
        try (FileInputStream fis = new FileInputStream(args[0])) {
            doc = dbf.newDocumentBuilder().parse(fis);
        }

        Element sigEl = (Element) doc.getElementsByTagNameNS(
            Constants.SignatureSpecNS, "Signature").item(0);
        if (sigEl == null) {
            System.err.println("INVALID: no ds:Signature element found");
            System.exit(1);
        }

        // xmlsec 4.x: secure validation is a constructor argument (blocks
        // RetrievalMethod loops, dangerous transforms, weak algorithms, etc.).
        XMLSignature signature = new XMLSignature(sigEl, "", true);

        boolean ok;
        if (args.length >= 2) {
            try (FileInputStream cf = new FileInputStream(args[1])) {
                X509Certificate pinned = (X509Certificate) CertificateFactory
                    .getInstance("X.509").generateCertificate(cf);
                ok = signature.checkSignatureValue(pinned.getPublicKey());
                System.out.println("verifying against pinned cert: "
                    + pinned.getSubjectX500Principal());
            }
        } else {
            X509Certificate embedded =
                signature.getKeyInfo().getX509Certificate();
            PublicKey pk = embedded != null ? embedded.getPublicKey()
                : signature.getKeyInfo().getPublicKey();
            ok = signature.checkSignatureValue(pk);
            System.out.println("verifying against KeyInfo-embedded key"
                + (embedded != null ? " (cert: "
                   + embedded.getSubjectX500Principal() + ")" : ""));
        }

        System.out.println(ok ? "VALID: signature OK" : "INVALID: signature check failed");
        System.exit(ok ? 0 : 1);
    }
}
