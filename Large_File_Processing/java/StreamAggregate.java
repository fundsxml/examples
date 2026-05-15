// Constant-memory aggregation over a huge FundsXML file via StAX (native Java,
// no JAXB, no DOM). Pull parser — never holds more than the current element.
//
//   javac -d /tmp/lf Large_File_Processing/java/StreamAggregate.java
//   java  -cp /tmp/lf StreamAggregate <fundsxml.xml>
//
// FundsXML 4.x has no XML namespace — match the bare "Position" local name.
// Security: external entities / DTDs disabled (XXE-safe).

import java.io.FileInputStream;
import javax.xml.stream.XMLInputFactory;
import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamReader;

public class StreamAggregate {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: StreamAggregate <fundsxml.xml>");
            System.exit(2);
        }

        XMLInputFactory xif = XMLInputFactory.newInstance();
        xif.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
        xif.setProperty(XMLInputFactory.SUPPORT_DTD, false);

        long n = 0;
        double sumValue = 0, sumPct = 0;
        boolean inPosition = false, inTotalValue = false;
        String currentLeaf = null;

        try (FileInputStream in = new FileInputStream(args[0])) {
            XMLStreamReader r = xif.createXMLStreamReader(in);
            while (r.hasNext()) {
                switch (r.next()) {
                    case XMLStreamConstants.START_ELEMENT: {
                        String name = r.getLocalName();
                        if ("Position".equals(name)) { inPosition = true; n++; }
                        else if ("TotalValue".equals(name)) inTotalValue = true;
                        currentLeaf = name;
                        break;
                    }
                    case XMLStreamConstants.CHARACTERS: {
                        if (!inPosition || r.isWhiteSpace()) break;
                        String t = r.getText().trim();
                        if (t.isEmpty()) break;
                        if (inTotalValue && "Amount".equals(currentLeaf))
                            sumValue += Double.parseDouble(t);
                        else if ("TotalPercentage".equals(currentLeaf))
                            sumPct += Double.parseDouble(t);
                        break;
                    }
                    case XMLStreamConstants.END_ELEMENT: {
                        String name = r.getLocalName();
                        if ("Position".equals(name)) inPosition = false;
                        else if ("TotalValue".equals(name)) inTotalValue = false;
                        currentLeaf = null;
                        break;
                    }
                    default:
                }
            }
            r.close();
        }

        Runtime rt = Runtime.getRuntime();
        long usedMiB = (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024);
        System.out.printf("positions      : %d%n", n);
        System.out.printf("sum value (EUR): %.2f%n", sumValue);
        System.out.printf("sum percentage : %.4f%n", sumPct);
        System.out.printf("heap in use    : %d MiB%n", usedMiB);
    }
}
