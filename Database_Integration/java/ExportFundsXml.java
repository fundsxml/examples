// =============================================================================
// EXPORT  —  relational database  ->  FundsXML file  (Java, SQLite via JDBC).
//
// Standalone, copy-me example of ONE direction (DB -> FundsXML). The reverse
// is a separate program, ImportFundsXml.java. Over-commented as documentation.
//
// DB SCHEMA  ../ddl/schema.sql  (already populated by ImportFundsXml).
//
// RUN  Standalone & cross-platform, from the repo root via the Maven Wrapper:
//   ./mvnw -q -pl Database_Integration/java compile exec:java \
//     -Dexec.mainClass=ExportFundsXml -Dexec.args="fx.db FUNDSXML_MULTI_1 out.xml"
//
// DEPENDENCIES  org.xerial:sqlite-jdbc (Maven Central, see pom.xml) + the JDK
//   (native javax.xml, no JAXB).
//
// FUNDSXML NOTES
//   * No XML namespace -> plain element names.
//   * Output normalized to the 4.2.9 schema URL; constants the model does not
//     store (TotalAssetNature=OFFICIAL, Price ActionCode=C / PriceNature=
//     OFFICIAL) reproduced verbatim so the round-trip compares equal
//     (../tools/xml_equiv.py, always paired with XSD validation).
//   * ORDER BY the 1-based *_seq columns reproduces the original order of
//     multiple funds / portfolios / positions.
// =============================================================================
import java.io.FileOutputStream;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Locale;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

public class ExportFundsXml {

    static final String SCHEMA_URL =
        "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd";
    static final String XSI = "http://www.w3.org/2001/XMLSchema-instance";
    static final java.util.Set<String> POSITION_KINDS = java.util.Set.of(
        "Equity", "Bond", "ShareClass", "Warrant", "Certificate", "Option",
        "Future", "FXForward", "Swap", "Repo", "RealEstate", "CallMoney",
        "Account", "Generic");
    static final java.util.Map<String, String> QTY_ELEM = java.util.Map.of(
        "Equity", "Units", "Warrant", "Units", "Certificate", "Units",
        "Bond", "Nominal", "ShareClass", "Shares",
        "Option", "Contracts", "Future", "Contracts");

    /** Amounts: DDL scale 2 (see num). */
    static String f2(double v) { return num(v, 2, 2); }

    /**
     * Number formatting follows the DDL scale (schema.sql): amounts
     * DECIMAL(20,2), TotalPercentage DECIMAL(9,4), quantities / NavPrice /
     * SharesOutstanding DECIMAL(28,6). Render at that scale, then drop trailing
     * zeros down to a floor of {@code minDec} decimals: 8.33 -> "8.33",
     * 8.3333 -> "8.3333", 550000 shares -> "550000". A fixed "%.2f" would
     * silently truncate what the model can store (xml_equiv.py compares
     * numerically and would flag the loss).
     */
    static String num(double v, int scale, int minDec) {
        java.math.BigDecimal d = java.math.BigDecimal.valueOf(v)
            .setScale(scale, java.math.RoundingMode.HALF_UP).stripTrailingZeros();
        if (d.scale() < minDec) d = d.setScale(minDec);
        return d.toPlainString();
    }

    /** Append <tag>text</tag> to parent (the one XML-build primitive). */
    static Element el(Document doc, org.w3c.dom.Node parent, String tag,
                      String text) {
        Element e = doc.createElement(tag);
        if (text != null) e.setTextContent(text);
        parent.appendChild(e);
        return e;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            System.err.println(
                "usage: ExportFundsXml <db> <document_id> <out.xml>");
            System.exit(2);
        }
        String db = args[0], docId = args[1], out = args[2];

        Document doc = DocumentBuilderFactory.newInstance()
            .newDocumentBuilder().newDocument();
        Element root = doc.createElement("FundsXML4");
        root.setAttribute("xmlns:xsi", XSI);
        root.setAttribute("xsi:noNamespaceSchemaLocation", SCHEMA_URL);
        doc.appendChild(root);

        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            // Bind the id (never concatenate user input into SQL) — the same
            // rule every other query in this file follows.
            PreparedStatement dq = c.prepareStatement(
                "SELECT * FROM document WHERE document_id = ?");
            dq.setString(1, docId);
            ResultSet d = dq.executeQuery();
            if (!d.next()) throw new RuntimeException("no document " + docId);

            Element cd = el(doc, root, "ControlData", null);
            el(doc, cd, "UniqueDocumentID", d.getString("document_id"));
            // Regenerate timestamp; xml_equiv.py ignores its value.
            String gen = d.getString("generated");
            el(doc, cd, "DocumentGenerated",
                gen != null ? gen : "2025-10-02T00:00:00");
            String ver = d.getString("version");
            if (ver != null) el(doc, cd, "Version", ver);  // none for 4.0.0
            el(doc, cd, "ContentDate", d.getString("content_date"));
            Element ds = el(doc, cd, "DataSupplier", null);
            el(doc, ds, "SystemCountry", d.getString("supplier_country"));
            el(doc, ds, "Short", d.getString("supplier_short"));
            el(doc, ds, "Name", d.getString("supplier_name"));
            el(doc, ds, "Type", d.getString("supplier_type"));
            el(doc, cd, "DataOperation", d.getString("data_operation"));

            Element fundsEl = el(doc, root, "Funds", null);
            PreparedStatement fps = c.prepareStatement(
                "SELECT * FROM fund WHERE document_id=? ORDER BY fund_seq");
            fps.setString(1, docId);
            ResultSet fr = fps.executeQuery();
            while (fr.next()) {
                int fundSeq = fr.getInt("fund_seq");
                String ccy = fr.getString("currency");
                String navDate = fr.getString("nav_date");
                Element fund = el(doc, fundsEl, "Fund", null);
                if (fr.getString("lei") != null)
                    el(doc, el(doc, fund, "Identifiers", null), "LEI",
                       fr.getString("lei"));
                el(doc, el(doc, fund, "Names", null), "OfficialName",
                   fr.getString("official_name"));
                el(doc, fund, "Currency", ccy);
                if (fr.getString("single_fund_flag") != null)
                    el(doc, fund, "SingleFundFlag",
                       fr.getString("single_fund_flag"));

                Element fdd = el(doc, fund, "FundDynamicData", null);
                Element tav = el(doc, el(doc, el(doc, fdd,
                    "TotalAssetValues", null), "TotalAssetValue", null),
                    "NavDate", navDate);
                Element tavp = (Element) tav.getParentNode();
                el(doc, tavp, "TotalAssetNature", "OFFICIAL");
                Element amt = el(doc, el(doc, tavp, "TotalNetAssetValue",
                    null), "Amount", f2(fr.getDouble("total_nav")));
                amt.setAttribute("ccy", ccy);

                Element ports = el(doc, fdd, "Portfolios", null);
                PreparedStatement pps = c.prepareStatement(
                    "SELECT * FROM portfolio WHERE document_id=? AND fund_seq=?"
                    + " ORDER BY portfolio_seq");
                pps.setString(1, docId); pps.setInt(2, fundSeq);
                ResultSet pr = pps.executeQuery();
                while (pr.next()) {
                    int portSeq = pr.getInt("portfolio_seq");
                    Element pe = el(doc, ports, "Portfolio", null);
                    el(doc, pe, "NavDate", pr.getString("nav_date"));
                    Element poss = el(doc, pe, "Positions", null);
                    PreparedStatement qps = c.prepareStatement(
                        "SELECT * FROM position WHERE document_id=? AND "
                        + "fund_seq=? AND portfolio_seq=? ORDER BY position_seq");
                    qps.setString(1, docId); qps.setInt(2, fundSeq);
                    qps.setInt(3, portSeq);
                    ResultSet qr = qps.executeQuery();
                    while (qr.next()) {
                        Element pos = el(doc, poss, "Position", null);
                        el(doc, pos, "UniqueID", qr.getString("unique_id"));
                        if (qr.getString("isin") != null)
                            el(doc, el(doc, pos, "Identifiers", null), "ISIN",
                               qr.getString("isin"));
                        if (qr.getString("currency") != null)
                            el(doc, pos, "Currency", qr.getString("currency"));
                        Element tv = el(doc, el(doc, pos, "TotalValue", null),
                            "Amount", f2(qr.getDouble("value_fund_ccy")));
                        tv.setAttribute("ccy", ccy);
                        el(doc, pos, "TotalPercentage",
                           num(qr.getDouble("percentage"), 4, 2));
                        String kind = qr.getString("kind");
                        if (kind == null || !POSITION_KINDS.contains(kind))
                            kind = "Generic";
                        Element ke = el(doc, pos, kind, null);
                        Object q = qr.getObject("kind_qty");
                        if (QTY_ELEM.containsKey(kind) && q != null)
                            el(doc, ke, QTY_ELEM.get(kind),
                               num(((Number) q).doubleValue(), 6, 2));
                    }
                }

                PreparedStatement sps = c.prepareStatement(
                    "SELECT * FROM share_class WHERE document_id=? AND "
                    + "fund_seq=? ORDER BY isin");
                sps.setString(1, docId); sps.setInt(2, fundSeq);
                ResultSet sr = sps.executeQuery();
                Element sce = null;
                while (sr.next()) {
                    if (sce == null)
                        sce = el(doc, el(doc, fund, "SingleFund", null),
                                 "ShareClasses", null);
                    Element x = el(doc, sce, "ShareClass", null);
                    el(doc, el(doc, x, "Identifiers", null), "ISIN",
                       sr.getString("isin"));
                    if (sr.getString("official_name") != null)
                        el(doc, el(doc, x, "Names", null), "OfficialName",
                           sr.getString("official_name"));
                    el(doc, x, "Currency", sr.getString("currency"));
                    Object navp = sr.getObject("nav_price");
                    if (navp != null) {
                        Element pe2 = el(doc, el(doc, x, "Prices", null),
                            "Price", null);
                        el(doc, pe2, "ActionCode", "C");
                        el(doc, pe2, "NavDate", navDate);
                        el(doc, pe2, "PriceCurrency", sr.getString("currency"));
                        el(doc, pe2, "PriceNature", "OFFICIAL");
                        el(doc, pe2, "NavPrice",
                           num(((Number) navp).doubleValue(), 6, 2));
                    }
                    Object navf = sr.getObject("nav_fund_ccy");
                    if (navf != null) {
                        Element t2 = el(doc, el(doc, x, "TotalAssetValues",
                            null), "TotalAssetValue", null);
                        el(doc, t2, "NavDate", navDate);
                        el(doc, t2, "TotalAssetNature", "OFFICIAL");
                        Element a2 = el(doc, el(doc, t2,
                            "TotalNetAssetValue", null), "Amount",
                            f2(((Number) navf).doubleValue()));
                        a2.setAttribute("ccy", ccy);
                        Object so = sr.getObject("shares_outstanding");
                        if (so != null)
                            el(doc, t2, "SharesOutstanding",
                               num(((Number) so).doubleValue(), 6, 0));
                    }
                }
            }

            PreparedStatement aps = c.prepareStatement(
                "SELECT * FROM asset WHERE document_id=? ORDER BY unique_id");
            aps.setString(1, docId);
            ResultSet ar = aps.executeQuery();
            Element amd = null;
            while (ar.next()) {
                if (amd == null) amd = el(doc, root, "AssetMasterData", null);
                Element ae = el(doc, amd, "Asset", null);
                el(doc, ae, "UniqueID", ar.getString("unique_id"));
                if (ar.getString("isin") != null)
                    el(doc, el(doc, ae, "Identifiers", null), "ISIN",
                       ar.getString("isin"));
                el(doc, ae, "Currency", ar.getString("currency"));
                if (ar.getString("country") != null)
                    el(doc, ae, "Country", ar.getString("country"));
                el(doc, ae, "Name", ar.getString("name"));
                el(doc, ae, "AssetType", ar.getString("asset_type"));
            }
        }

        Transformer tr = TransformerFactory.newInstance().newTransformer();
        tr.setOutputProperty(OutputKeys.ENCODING, "UTF-8");
        tr.setOutputProperty(OutputKeys.INDENT, "yes");
        try (FileOutputStream os = new FileOutputStream(out)) {
            tr.transform(new DOMSource(doc), new StreamResult(os));
        }
        System.out.println("wrote " + out);
    }
}
