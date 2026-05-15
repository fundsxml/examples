// XSD validation in native Java (no JAXB) via javax.xml.validation.
//
// Single-file program — run directly with a modern JDK (11+):
//   java XSD_Validation/java/XsdValidate.java <version> <xml-file>
// Exit: 0 = valid, 1 = invalid, 2 = usage/setup error
//
// Validates against the official released schema, materialized locally by
// tools/fetch-schema.sh (handles the GitHub 302 redirect and the relative
// xmldsig-core-schema.xsd import that FundsXML 4.2.9+ requires).
//
// Security: FEATURE_SECURE_PROCESSING on, external DTD/schema access denied,
// XXE vectors closed. FundsXML needs no external entities.

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
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

        Path repoRoot = Paths.get(System.getProperty("user.dir"));
        File schema = repoRoot.resolve(".schema-cache").resolve(version)
                              .resolve("FundsXML.xsd").toFile();
        if (!schema.isFile()) {
            System.err.println("schema not cached; run: tools/fetch-schema.sh " + version);
            System.exit(2);
        }

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
}
