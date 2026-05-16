// Native Java data binding for FundsXML — DOM + XPath into records, NO JAXB.
//
// Standalone & cross-platform — run from the repo root with the Maven Wrapper:
//   ./mvnw -q -pl Data_Binding_JSON/java compile exec:java \
//       -Dexec.args="<fundsxml.xml>"
//
// Why no JAXB: the FundsXML schema is huge; generating/maintaining a full JAXB
// model is heavy and brittle across versions. For most integration work a thin
// hand-written binding over DOM/XPath is simpler, version-tolerant (FundsXML
// 4.x is backward compatible) and dependency-free. The codegen alternatives
// (JAXB xjc, xsdata, xsd.exe) are documented in the README.
//
// FundsXML 4.x has no XML namespace — XPath uses bare element names.
// Security: namespace-unaware is fine here; DTDs/external entities disabled.

import java.io.FileInputStream;
import java.util.ArrayList;
import java.util.List;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class NativeBinding {

    // Immutable binding types (Java records).
    record Fund(String lei, String name, String currency, double totalNav,
                int positionCount) {}
    record Position(String uniqueId, String isin, double value,
                    double percentage, String kind) {}

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: NativeBinding <fundsxml.xml>");
            System.exit(2);
        }

        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.setExpandEntityReferences(false);
        Document doc;
        try (FileInputStream in = new FileInputStream(args[0])) {
            doc = dbf.newDocumentBuilder().parse(in);
        }
        XPath xp = XPathFactory.newInstance().newXPath();

        String ccy = xp.evaluate("/FundsXML4/Funds/Fund/Currency", doc);
        Fund fund = new Fund(
            xp.evaluate("/FundsXML4/Funds/Fund/Identifiers/LEI", doc),
            xp.evaluate("/FundsXML4/Funds/Fund/Names/OfficialName", doc),
            ccy,
            Double.parseDouble(xp.evaluate(
                "/FundsXML4/Funds/Fund/FundDynamicData/TotalAssetValues/"
                + "TotalAssetValue/TotalNetAssetValue/Amount[@ccy='" + ccy
                + "']", doc)),
            ((Number) xp.evaluate(
                "count(//Position)", doc, XPathConstants.NUMBER)).intValue());

        NodeList pn = (NodeList) xp.evaluate("//Positions/Position", doc,
                                             XPathConstants.NODESET);
        List<Position> positions = new ArrayList<>();
        double sumPct = 0;
        for (int i = 0; i < pn.getLength(); i++) {
            Node p = pn.item(i);
            String kind = xp.evaluate(
                "local-name(*[local-name()='Equity' or local-name()='Bond' "
                + "or local-name()='ShareClass' or local-name()='Warrant' "
                + "or local-name()='Certificate' or local-name()='Option' "
                + "or local-name()='Future' or local-name()='FXForward' "
                + "or local-name()='Swap' or local-name()='Repo' "
                + "or local-name()='RealEstate' or local-name()='CallMoney'][1])",
                p);
            double pct = num(xp.evaluate("TotalPercentage", p));
            sumPct += pct;
            positions.add(new Position(
                xp.evaluate("UniqueID", p),
                xp.evaluate("Identifiers/ISIN", p),
                num(xp.evaluate("TotalValue/Amount[@ccy='" + ccy + "']", p)),
                pct, kind));
        }

        System.out.println("Fund      : " + fund.name());
        System.out.println("LEI / ccy : " + fund.lei() + " / " + fund.currency());
        System.out.printf("Total NAV : %.2f%n", fund.totalNav());
        System.out.println("Positions : " + fund.positionCount());
        System.out.printf("Sum %%     : %.4f%n", sumPct);
        System.out.println("First 3   :");
        positions.stream().limit(3).forEach(p -> System.out.printf(
            "  %s %-12s %14.2f  %6.2f%%  [%s]%n",
            p.uniqueId(), p.isin(), p.value(), p.percentage(), p.kind()));
    }

    private static double num(String s) {
        return (s == null || s.isBlank()) ? 0.0 : Double.parseDouble(s.trim());
    }
}
