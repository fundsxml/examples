// Native-Java Schematron validation using the SchXslt Java API.
//
// Compile + run against the SchXslt CLI classpath (it bundles Saxon):
//   tools/fetch-tools.sh   # populates .lib/
//   CP=.lib/schxslt-cli-1.10.1.jar:.lib/commons-cli-1.5.0.jar:\
//      .lib/slf4j-api-1.7.32.jar:.lib/slf4j-nop-1.7.32.jar
//   javac -cp "$CP" -d /tmp Schematron_DataQuality_Checks/Basic_Checks/invocation/SchematronValidate.java
//   java -cp "$CP:/tmp" SchematronValidate basic_checks.sch document.xml
//
// Exit: 0 = no error-role failed-assert, 1 = at least one, 2 = setup error.
//
// Why this classpath: basic_checks.sch uses queryBinding="xslt2". SchXslt
// compiles the Schematron to XSLT 2.0 and Saxon (bundled in the SchXslt CLI
// jar) executes it. Do NOT add the standalone Saxon-HE jar — its org.xmlresolver
// API differs from the one SchXslt bundles and the two conflict.

import java.io.File;
import javax.xml.transform.stream.StreamSource;
import name.dmaus.schxslt.Schematron;
import name.dmaus.schxslt.Result;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class SchematronValidate {

    private static final String SVRL_NS = "http://purl.oclc.org/dsdl/svrl";

    public static void main(String[] args) {
        if (args.length != 2) {
            System.err.println("usage: SchematronValidate <schema.sch> <xml-file>");
            System.exit(2);
        }
        try {
            Schematron schematron =
                new Schematron(new StreamSource(new File(args[0])));
            Result result =
                schematron.validate(new StreamSource(new File(args[1])));
            Document svrl = result.getValidationReport();

            int errors = 0, warnings = 0, reports = 0;
            NodeList fa = svrl.getElementsByTagNameNS(SVRL_NS, "failed-assert");
            for (int i = 0; i < fa.getLength(); i++) {
                Element e = (Element) fa.item(i);
                String role = e.getAttribute("role");
                String text = textOf(e);
                if ("error".equalsIgnoreCase(role)) {
                    errors++;
                    System.out.println("ERROR   " + text);
                } else {
                    warnings++;
                    System.out.println("WARNING " + text);
                }
            }
            NodeList sr =
                svrl.getElementsByTagNameNS(SVRL_NS, "successful-report");
            for (int i = 0; i < sr.getLength(); i++) {
                reports++;
                System.out.println("REPORT  " + textOf((Element) sr.item(i)));
            }

            System.out.printf("%nsummary: %d error(s), %d warning(s), "
                              + "%d report(s)%n", errors, warnings, reports);
            System.exit(errors > 0 ? 1 : 0);
        } catch (Exception ex) {
            System.err.println("setup/processing error: " + ex.getMessage());
            System.exit(2);
        }
    }

    private static String textOf(Element parent) {
        NodeList t = parent.getElementsByTagNameNS(SVRL_NS, "text");
        return t.getLength() > 0
            ? t.item(0).getTextContent().trim().replaceAll("\\s+", " ")
            : "";
    }
}
