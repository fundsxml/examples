// XSD validation in native Java (no JAXB) via javax.xml.validation.
//
// Standalone & cross-platform — no prior tool, no bash, works on Windows.
// Run from the repo root with the committed Maven Wrapper:
//   ./mvnw -q -pl XSD_Validation/java compile exec:java \
//       -Dexec.args="https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd \
//                     FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml"
// Exit: 0 = valid, 1 = invalid, 2 = usage/setup error
//
// You give it exactly two things: the schema and the instance. <schema> is a
// path to an XSD file OR a remote URL (e.g. the official release shown above).
// No version, no env var, no cache, no resolver — whatever you point at is
// used as-is. For FundsXML 4.2.9+ the schema imports xmldsig-core-schema.xsd
// via a relative path, so that sibling must be reachable next to <schema>
// (it is, in the official release directory and in any complete local copy).
//
// A URL schema (and, when imported, the xmldsig sibling) is fetched into a
// temp dir first, then validated from there. The official release URL 302-
// redirects to an opaque blob URL; resolving the schema's *relative* xmldsig
// import against that post-redirect URL would fail, so the fetch is done
// here (it also keeps the 302 handled) and the relative import then resolves
// locally — identical behaviour for a path or a URL.
//
// Security: FEATURE_SECURE_PROCESSING on; the instance's external DTD access
// is denied (ACCESS_EXTERNAL_DTD = ""), closing XXE vectors. Only the trusted,
// user-supplied schema is fetched over the network.

import java.io.File;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import javax.xml.validation.Validator;
import org.xml.sax.ErrorHandler;
import org.xml.sax.SAXParseException;

public class XsdValidate {

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: XsdValidate <schema> <xml-file>");
            System.exit(2);
        }
        String schemaArg = args[0];
        String xmlFile = args[1];

        Path tmpDir = null;
        File schemaFile;
        try {
            if (schemaArg.matches("^https?://.*")) {
                tmpDir = Files.createTempDirectory("fxsd");
                Path local = tmpDir.resolve("FundsXML.xsd");
                download(schemaArg, local);
                // FundsXML 4.2.9+ imports xmldsig-core-schema.xsd via a
                // relative path; fetch that sibling from the same URL dir
                // only when it is actually referenced.
                if (Files.readString(local).contains("xmldsig-core-schema.xsd")) {
                    String sib = schemaArg.substring(
                        0, schemaArg.lastIndexOf('/') + 1)
                        + "xmldsig-core-schema.xsd";
                    download(sib, tmpDir.resolve("xmldsig-core-schema.xsd"));
                }
                schemaFile = local.toFile();
            } else {
                schemaFile = new File(schemaArg);
            }

            SchemaFactory factory =
                SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            // Local file access only — the schema is already materialised;
            // the instance's DTD access stays denied (XXE hardening).
            factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "file");
            factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");

            Schema fundsXmlSchema = factory.newSchema(schemaFile);
            Validator validator = fundsXmlSchema.newValidator();
            validator.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            validator.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "file");

            final boolean[] failed = {false};
            validator.setErrorHandler(new ErrorHandler() {
                public void warning(SAXParseException e) { }
                public void error(SAXParseException e) { report(e); }
                public void fatalError(SAXParseException e) { report(e); }
                private void report(SAXParseException e) {
                    failed[0] = true;
                    System.err.println("  line " + e.getLineNumber() + ": "
                                       + e.getMessage());
                }
            });

            try {
                validator.validate(new StreamSource(new File(xmlFile)));
            } catch (SAXParseException e) {
                failed[0] = true;
                System.err.println("  line " + e.getLineNumber() + ": "
                                   + e.getMessage());
            }

            if (failed[0]) {
                System.err.println("INVALID: " + xmlFile + " (schema "
                                   + schemaArg + ")");
                System.exit(1);
            }
            System.out.println("VALID: " + xmlFile + " (schema "
                               + schemaArg + ")");
        } finally {
            if (tmpDir != null) {
                try (var paths = Files.walk(tmpDir)) {
                    paths.sorted(java.util.Comparator.reverseOrder())
                         .forEach(p -> p.toFile().delete());
                }
            }
        }
    }

    /** GET {@code url} (following the GitHub 302) into {@code out}. */
    static void download(String url, Path out) throws Exception {
        System.err.println("schema: fetch " + url);
        HttpClient client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NORMAL).build();
        HttpResponse<byte[]> resp = client.send(
            HttpRequest.newBuilder(URI.create(url)).GET().build(),
            HttpResponse.BodyHandlers.ofByteArray());
        if (resp.statusCode() != 200) {
            System.err.println("download failed (HTTP " + resp.statusCode()
                + "): " + url);
            System.exit(2);
        }
        Files.write(out, resp.body());
    }
}
