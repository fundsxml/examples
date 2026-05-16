// XSD validation in native Java (no JAXB) via javax.xml.validation.
//
// Standalone & cross-platform — no prior tool, no bash, works on Windows.
// Run from the repo root with the committed Maven Wrapper:
//   ./mvnw -q -pl XSD_Validation/java compile exec:java \
//       -Dexec.args="4.2.9 FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml"
// Exit: 0 = valid, 1 = invalid, 2 = usage/setup error
//
// The official released schema is obtained by this program itself, in this
// order (identical convention across all stacks):
//   1. $FUNDSXML_SCHEMA_DIR   — a directory holding FundsXML.xsd (+ the
//      xmldsig-core-schema.xsd sibling for 4.2.9+). Used as-is, NO network.
//      The escape hatch for locked-down corporate networks / offline use.
//   2. .schema-cache/<version>/FundsXML.xsd — reused if already present.
//   3. download from the official GitHub release (following the 302), caching
//      into .schema-cache/<version>/; the relative xmldsig-core-schema.xsd
//      sibling is fetched only when FundsXML.xsd actually imports it (4.2.9+).
// The source of truth stays the official release URL — no committed catalog.
//
// Security: FEATURE_SECURE_PROCESSING on, external DTD/schema access denied,
// XXE vectors closed. FundsXML needs no external entities.

import java.io.File;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
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
            System.err.println("usage: XsdValidate <version> <xml-file>");
            System.exit(2);
        }
        String version = args[0];
        String xmlFile = args[1];

        File schema = resolveSchema(version).toFile();

        SchemaFactory factory =
            SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        // Allow only local file access so the relative xmldsig-core-schema.xsd
        // import (4.2.9+) resolves; block http/external fetches.
        factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "file");
        factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");

        Schema fundsXmlSchema = factory.newSchema(schema);
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
            System.err.println("INVALID: " + xmlFile + " (FundsXML " + version + ")");
            System.exit(1);
        }
        System.out.println("VALID: " + xmlFile + " (FundsXML " + version + ")");
    }

    static final String RELEASE_BASE =
        "https://github.com/fundsxml/schema/releases/download/";

    /**
     * Resolve FundsXML.xsd for {@code version}: env-var dir, else local cache,
     * else download from the official GitHub release (caching the result).
     * The xmldsig-core-schema.xsd sibling is fetched only when imported.
     */
    static Path resolveSchema(String version) throws Exception {
        // 1. Offline / corporate-network escape hatch: a hand-placed copy.
        String envDir = System.getenv("FUNDSXML_SCHEMA_DIR");
        if (envDir != null && !envDir.isBlank()) {
            Path xsd = Paths.get(envDir, "FundsXML.xsd");
            if (!Files.isRegularFile(xsd)) {
                System.err.println("FUNDSXML_SCHEMA_DIR set but "
                    + xsd + " not found");
                System.exit(2);
            }
            System.err.println("schema: using $FUNDSXML_SCHEMA_DIR -> " + xsd);
            return xsd;
        }

        // 2. Local cache (shared by every stack, gitignored).
        Path cacheDir = Paths.get(System.getProperty("user.dir"),
            ".schema-cache", version);
        Path xsd = cacheDir.resolve("FundsXML.xsd");
        if (Files.isRegularFile(xsd)) {
            System.err.println("schema: cached -> " + xsd);
            return xsd;
        }

        // 3. Download from the official release (source of truth).
        Files.createDirectories(cacheDir);
        download(RELEASE_BASE + version + "/FundsXML.xsd", xsd);
        // From 4.2.9 on, FundsXML.xsd imports xmldsig-core-schema.xsd via a
        // relative path — it must sit next to FundsXML.xsd or the schema does
        // not compile. Fetch the sibling only when it is actually referenced.
        if (Files.readString(xsd).contains("xmldsig-core-schema.xsd")) {
            download(RELEASE_BASE + version + "/xmldsig-core-schema.xsd",
                cacheDir.resolve("xmldsig-core-schema.xsd"));
        }
        return xsd;
    }

    /** GET {@code url} (following the GitHub 302) atomically into {@code out}. */
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
        Path tmp = Files.createTempFile(out.getParent(), "xsd", ".part");
        Files.write(tmp, resp.body());
        Files.move(tmp, out, StandardCopyOption.REPLACE_EXISTING);
    }
}
