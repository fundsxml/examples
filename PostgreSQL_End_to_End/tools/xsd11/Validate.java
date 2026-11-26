// XSD 1.1 validation with Xerces-J 2.12.2 (the JDK's built-in validator only knows XSD 1.0).
// Run through validate.sh, which puts the Xerces jars on the class path.
// Usage: java Validate.java <schema.xsd> <file.xml>...   exit code 0 = all valid
import java.io.File;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.*;
import org.xml.sax.*;

public class Validate {
    public static void main(String[] args) throws Exception {
        SchemaFactory factory = SchemaFactory.newInstance("http://www.w3.org/XML/XMLSchema/v1.1",
                "org.apache.xerces.jaxp.validation.XMLSchema11Factory", null);
        Schema schema = factory.newSchema(new File(args[0]));
        int invalid = 0;
        for (int i = 1; i < args.length; i++) {
            String file = args[i];
            int[] errors = {0};
            Validator validator = schema.newValidator();
            validator.setErrorHandler(new ErrorHandler() {
                public void warning(SAXParseException e) { report("WARN", e); }
                public void error(SAXParseException e) { errors[0]++; report("ERROR", e); }
                public void fatalError(SAXParseException e) { errors[0]++; report("FATAL", e); }
                void report(String level, SAXParseException e) {
                    System.out.println(file + ":" + e.getLineNumber() + " " + level + " " + e.getMessage());
                }
            });
            try {
                validator.validate(new StreamSource(new File(file)));
            } catch (SAXParseException e) {
                // a fatal error (not well-formed) was reported above; go on with the next file
            }
            System.out.println(file + (errors[0] == 0 ? ": valid (XSD 1.1)" : ": " + errors[0] + " error(s)"));
            if (errors[0] > 0) invalid++;
        }
        System.exit(invalid == 0 ? 0 : 1);
    }
}
