// SignFundsXml — enveloped XML-DSig signing with Apache Santuario (xmlsec 4.x).
//
//   tools/fetch-tools.sh
//   XML_Signature/generate-test-key.sh
//   CP=.lib/xmlsec-4.0.4.jar:.lib/commons-codec-1.18.0.jar:\
//      .lib/slf4j-api-2.0.17.jar:.lib/slf4j-nop-2.0.17.jar
//   javac -cp "$CP" -d /tmp/sig XML_Signature/java/SignFundsXml.java
//   java  -cp "$CP:/tmp/sig" SignFundsXml <in.xml> <out.xml> \
//         XML_Signature/keys/test-signing.p12 changeit fundsxml
//
// Produces an enveloped signature whose ds:Signature is appended as the last
// child of <FundsXML4> — exactly where the FundsXML 4.2.9 schema allows it
// (xmldsig-core-schema.xsd import). The signer certificate is embedded in
// KeyInfo/X509Data so the signed file is self-verifiable.
//
// Security: DocumentBuilderFactory is namespace-aware and XXE-hardened.

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.security.Key;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.apache.xml.security.Init;
import org.apache.xml.security.algorithms.MessageDigestAlgorithm;
import org.apache.xml.security.c14n.Canonicalizer;
import org.apache.xml.security.signature.XMLSignature;
import org.apache.xml.security.transforms.Transforms;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

public class SignFundsXml {
    public static void main(String[] args) throws Exception {
        if (args.length != 5) {
            System.err.println("usage: SignFundsXml <in.xml> <out.xml> "
                + "<keystore.p12> <storepass> <alias>");
            System.exit(2);
        }
        String in = args[0], out = args[1], ks = args[2],
               pass = args[3], alias = args[4];

        Init.init();

        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        Document doc;
        try (FileInputStream fis = new FileInputStream(in)) {
            doc = dbf.newDocumentBuilder().parse(fis);
        }

        KeyStore keyStore = KeyStore.getInstance("PKCS12");
        try (FileInputStream kfis = new FileInputStream(ks)) {
            keyStore.load(kfis, pass.toCharArray());
        }
        Key key = keyStore.getKey(alias, pass.toCharArray());
        X509Certificate cert = (X509Certificate) keyStore.getCertificate(alias);

        Element root = doc.getDocumentElement();
        XMLSignature sig = new XMLSignature(doc, "",
            XMLSignature.ALGO_ID_SIGNATURE_RSA_SHA256,
            Canonicalizer.ALGO_ID_C14N_EXCL_OMIT_COMMENTS);

        // ds:Signature is the LAST allowed child of <FundsXML4>.
        root.appendChild(sig.getElement());

        Transforms tr = new Transforms(doc);
        tr.addTransform(Transforms.TRANSFORM_ENVELOPED_SIGNATURE);
        tr.addTransform(Canonicalizer.ALGO_ID_C14N_EXCL_OMIT_COMMENTS);
        sig.addDocument("", tr, MessageDigestAlgorithm.ALGO_ID_DIGEST_SHA256);

        sig.addKeyInfo(cert);
        sig.addKeyInfo(cert.getPublicKey());
        sig.sign((PrivateKey) key);

        Transformer t = TransformerFactory.newInstance().newTransformer();
        try (FileOutputStream fos = new FileOutputStream(out)) {
            t.transform(new DOMSource(doc), new StreamResult(fos));
        }
        System.out.println("signed -> " + out
            + " (RSA-SHA256, exclusive C14N, enveloped)");
    }
}
