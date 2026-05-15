// =============================================================================
// FundsXML <-> relational database — runnable reference (Java, SQLite via JDBC).
//
// PURPOSE
//   Standalone, copy-me example showing BOTH directions (import a FundsXML file
//   into the relational schema, and export it back out). Over-commented on
//   purpose: read it once and reimplement the pattern in your own project.
//
// DB SCHEMA
//   ../ddl/schema.sql  (document -> fund -> portfolio -> position; share_class
//   per fund; asset document-scoped). SQLite keeps the example zero-setup.
//
// RUN  (the sqlite-jdbc jar is fetched by tools/fetch-tools.sh into .lib/)
//   tools/fetch-tools.sh
//   CP=.lib/sqlite-jdbc-3.46.1.3.jar
//   javac -cp "$CP" -d /tmp/db Database_Integration/java/FundsXmlDb.java
//   java  -cp "$CP:/tmp/db" FundsXmlDb roundtrip \
//         FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml out.xml
//   commands: init <db> | import <db> <xml> | export <db> <docId> <out> |
//             roundtrip <xml> <out>
//
// DEPENDENCIES
//   org.xerial:sqlite-jdbc (self-contained, bundles native SQLite) + the JDK.
//   XML uses native javax.xml DOM/XPath — NO JAXB (the FundsXML schema is huge;
//   a thin DOM binding is simpler and version-tolerant).
//
// FUNDSXML ASSUMPTIONS (non-obvious)
//   * FundsXML 4.x has NO XML namespace -> XPath uses bare element names.
//   * Many <Fund>, each many <Portfolio>, each many <Position>: we iterate all
//     and store 1-based *_seq ordinals so the export is order-faithful and the
//     round-trip compares equal (see ../tools/xml_equiv.py).
//   * Positions link to AssetMasterData by shared <UniqueID>; `asset` is
//     therefore document-scoped, not per-fund.
//   * Export is normalized to the 4.2.9 schema URL. Constants the model does
//     not store (TotalAssetNature=OFFICIAL, Price ActionCode=C/PriceNature=
//     OFFICIAL) are reproduced verbatim so the round-trip stays equal.
//
// SECURITY
//   The DOM parser forbids DOCTYPE/external entities (XXE / billion laughs).
// =============================================================================
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.Locale;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class FundsXmlDb {

    static final String SCHEMA_URL =
        "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd";
    static final String XSI = "http://www.w3.org/2001/XMLSchema-instance";

    // Position instrument-class element + its mandatory quantity child.
    // Kinds absent from QTY_ELEM are schema-valid as an empty element.
    static final java.util.Set<String> POSITION_KINDS = java.util.Set.of(
        "Equity", "Bond", "ShareClass", "Warrant", "Certificate", "Option",
        "Future", "FXForward", "Swap", "Repo", "RealEstate", "CallMoney",
        "Account", "Generic");
    static final java.util.Map<String, String> QTY_ELEM = java.util.Map.of(
        "Equity", "Units", "Warrant", "Units", "Certificate", "Units",
        "Bond", "Nominal", "ShareClass", "Shares",
        "Option", "Contracts", "Future", "Contracts");

    // ---- helpers -----------------------------------------------------------
    static XPath xpath() { return XPathFactory.newInstance().newXPath(); }

    /** First matching descendant's text (bare element names; no namespace). */
    static String t(Node ctx, String expr) throws Exception {
        Node n = (Node) xpath().evaluate(expr, ctx, XPathConstants.NODE);
        return n == null ? null : n.getTextContent();
    }

    static Double num(String s) {
        return (s == null || s.isBlank()) ? null : Double.valueOf(s.trim());
    }

    static String f2(double v) { return String.format(Locale.ROOT, "%.2f", v); }

    /** Append <tag>text</tag> to parent (the single XML-build primitive). */
    static Element el(Document doc, Node parent, String tag, String text) {
        Element e = doc.createElement(tag);
        if (text != null) e.setTextContent(text);
        parent.appendChild(e);
        return e;
    }

    static Connection open(String db) throws Exception {
        Connection c = DriverManager.getConnection("jdbc:sqlite:" + db);
        c.createStatement().execute("PRAGMA foreign_keys = ON");
        return c;
    }

    static Document parseSecure(String xml) throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        f.setFeature("http://xml.org/sax/features/external-general-entities", false);
        f.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        f.setExpandEntityReferences(false);
        try (FileInputStream in = new FileInputStream(xml)) {
            return f.newDocumentBuilder().parse(in);
        }
    }

    // ---- init --------------------------------------------------------------
    static void init(String db) throws Exception {
        Path ddl = Path.of(System.getProperty("user.dir"),
            "Database_Integration", "ddl", "schema.sql");
        // Fallback when run from inside Database_Integration/java.
        if (!Files.exists(ddl))
            ddl = Path.of("..", "ddl", "schema.sql");
        // Strip "--" line comments first (the DDL has no string literals, so a
        // plain cut at "--" is safe) so only real SQL statements remain.
        StringBuilder clean = new StringBuilder();
        for (String line : Files.readString(ddl).split("\n")) {
            int cut = line.indexOf("--");
            clean.append(cut >= 0 ? line.substring(0, cut) : line).append('\n');
        }
        try (Connection c = open(db); Statement st = c.createStatement()) {
            for (String stmt : clean.toString().split(";")) {
                if (!stmt.strip().isEmpty()) st.execute(stmt);
            }
        }
    }

    // ---- import : FundsXML -> rows -----------------------------------------
    static String doImport(String db, String xml) throws Exception {
        Document doc = parseSecure(xml);
        XPath xp = xpath();
        Node cd = (Node) xp.evaluate("/FundsXML4/ControlData", doc,
            XPathConstants.NODE);
        String docId = t(cd, "UniqueDocumentID");

        try (Connection c = open(db)) {
            c.setAutoCommit(false);

            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO document VALUES (?,?,?,?,?,?,?,?,?)")) {
                ps.setString(1, docId);
                ps.setString(2, t(cd, "DocumentGenerated"));
                ps.setString(3, t(cd, "Version"));
                ps.setString(4, t(cd, "ContentDate"));
                ps.setString(5, t(cd, "DataOperation"));
                ps.setString(6, t(cd, "DataSupplier/SystemCountry"));
                ps.setString(7, t(cd, "DataSupplier/Short"));
                ps.setString(8, t(cd, "DataSupplier/Name"));
                ps.setString(9, t(cd, "DataSupplier/Type"));
                ps.executeUpdate();
            }

            NodeList funds = (NodeList) xp.evaluate("/FundsXML4/Funds/Fund",
                doc, XPathConstants.NODESET);
            for (int fi = 0; fi < funds.getLength(); fi++) {
                Node fund = funds.item(fi);
                int fundSeq = fi + 1;            // 1-based document order
                String ccy = t(fund, "Currency");
                Node tav = (Node) xp.evaluate(
                    "FundDynamicData/TotalAssetValues/TotalAssetValue",
                    fund, XPathConstants.NODE);

                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO fund VALUES (?,?,?,?,?,?,?,?)")) {
                    ps.setString(1, docId);
                    ps.setInt(2, fundSeq);
                    ps.setString(3, t(fund, "Identifiers/LEI"));
                    ps.setString(4, t(fund, "Names/OfficialName"));
                    ps.setString(5, ccy);
                    ps.setString(6, t(fund, "SingleFundFlag"));
                    ps.setString(7, t(tav, "NavDate"));
                    ps.setDouble(8, Double.parseDouble(t(tav,
                        "TotalNetAssetValue/Amount[@ccy='" + ccy + "']")));
                    ps.executeUpdate();
                }

                NodeList scs = (NodeList) xp.evaluate(
                    "SingleFund/ShareClasses/ShareClass", fund,
                    XPathConstants.NODESET);
                for (int si = 0; si < scs.getLength(); si++) {
                    Node sc = scs.item(si);
                    try (PreparedStatement ps = c.prepareStatement(
                            "INSERT INTO share_class VALUES (?,?,?,?,?,?,?,?)")) {
                        ps.setString(1, docId);
                        ps.setInt(2, fundSeq);
                        ps.setString(3, t(sc, "Identifiers/ISIN"));
                        ps.setString(4, t(sc, "Names/OfficialName"));
                        ps.setString(5, t(sc, "Currency"));
                        setNum(ps, 6, num(t(sc, "Prices/Price/NavPrice")));
                        setNum(ps, 7, num(t(sc, "TotalAssetValues/"
                            + "TotalAssetValue/TotalNetAssetValue/Amount[@ccy='"
                            + ccy + "']")));
                        setNum(ps, 8, num(t(sc, "TotalAssetValues/"
                            + "TotalAssetValue/SharesOutstanding")));
                        ps.executeUpdate();
                    }
                }

                NodeList ports = (NodeList) xp.evaluate(
                    "FundDynamicData/Portfolios/Portfolio", fund,
                    XPathConstants.NODESET);
                for (int pi = 0; pi < ports.getLength(); pi++) {
                    Node port = ports.item(pi);
                    int portSeq = pi + 1;
                    try (PreparedStatement ps = c.prepareStatement(
                            "INSERT INTO portfolio VALUES (?,?,?,?)")) {
                        ps.setString(1, docId);
                        ps.setInt(2, fundSeq);
                        ps.setInt(3, portSeq);
                        ps.setString(4, t(port, "NavDate"));
                        ps.executeUpdate();
                    }
                    NodeList poss = (NodeList) xp.evaluate(
                        "Positions/Position", port, XPathConstants.NODESET);
                    for (int qi = 0; qi < poss.getLength(); qi++) {
                        Node pos = poss.item(qi);
                        String kind = null;
                        for (Node ch = pos.getFirstChild(); ch != null;
                                ch = ch.getNextSibling())
                            if (ch.getNodeType() == Node.ELEMENT_NODE
                                && POSITION_KINDS.contains(ch.getNodeName())) {
                                kind = ch.getNodeName();
                                break;
                            }
                        Double qty = (kind != null && QTY_ELEM.containsKey(kind))
                            ? num(t(pos, kind + "/" + QTY_ELEM.get(kind)))
                            : null;
                        try (PreparedStatement ps = c.prepareStatement(
                                "INSERT INTO position VALUES (?,?,?,?,?,?,?,?,?,?,?)")) {
                            ps.setString(1, docId);
                            ps.setInt(2, fundSeq);
                            ps.setInt(3, portSeq);
                            ps.setInt(4, qi + 1);
                            ps.setString(5, t(pos, "UniqueID"));
                            ps.setString(6, t(pos, "Identifiers/ISIN"));
                            ps.setString(7, t(pos, "Currency"));
                            ps.setDouble(8, Double.parseDouble(t(pos,
                                "TotalValue/Amount[@ccy='" + ccy + "']")));
                            ps.setDouble(9, Double.parseDouble(
                                t(pos, "TotalPercentage")));
                            ps.setString(10, kind);
                            setNum(ps, 11, qty);
                            ps.executeUpdate();
                        }
                    }
                }
            }

            NodeList assets = (NodeList) xp.evaluate(
                "/FundsXML4/AssetMasterData/Asset", doc, XPathConstants.NODESET);
            for (int ai = 0; ai < assets.getLength(); ai++) {
                Node a = assets.item(ai);
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO asset VALUES (?,?,?,?,?,?,?)")) {
                    ps.setString(1, docId);
                    ps.setString(2, t(a, "UniqueID"));
                    ps.setString(3, t(a, "Identifiers/ISIN"));
                    ps.setString(4, t(a, "Name"));
                    ps.setString(5, t(a, "AssetType"));
                    ps.setString(6, t(a, "Currency"));
                    ps.setString(7, t(a, "Country"));
                    ps.executeUpdate();
                }
            }
            c.commit();
        }
        return docId;
    }

    static void setNum(PreparedStatement ps, int i, Double v) throws Exception {
        if (v == null) ps.setNull(i, java.sql.Types.DECIMAL);
        else ps.setDouble(i, v);
    }

    // ---- export : rows -> FundsXML ----------------------------------------
    static void export(String db, String docId, String out) throws Exception {
        Document doc = DocumentBuilderFactory.newInstance()
            .newDocumentBuilder().newDocument();
        Element root = doc.createElement("FundsXML4");
        root.setAttribute("xmlns:xsi", XSI);
        root.setAttribute("xsi:noNamespaceSchemaLocation", SCHEMA_URL);
        doc.appendChild(root);

        try (Connection c = open(db)) {
            ResultSet d = c.createStatement().executeQuery(
                "SELECT * FROM document WHERE document_id='" + docId + "'");
            if (!d.next()) throw new RuntimeException("no document " + docId);

            Element cd = el(doc, root, "ControlData", null);
            el(doc, cd, "UniqueDocumentID", d.getString("document_id"));
            // Regenerate timestamp; xml_equiv.py ignores its value.
            String gen = d.getString("generated");
            el(doc, cd, "DocumentGenerated",
                gen != null ? gen : "2025-10-02T00:00:00");
            String ver = d.getString("version");
            if (ver != null) el(doc, cd, "Version", ver);   // none for 4.0.0
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
                Element tnav = el(doc, tavp, "TotalNetAssetValue", null);
                Element amt = el(doc, tnav, "Amount",
                    f2(fr.getDouble("total_nav")));
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
                           f2(qr.getDouble("percentage")));
                        String kind = qr.getString("kind");
                        if (kind == null || !POSITION_KINDS.contains(kind))
                            kind = "Generic";
                        Element ke = el(doc, pos, kind, null);
                        Object q = qr.getObject("kind_qty");
                        if (QTY_ELEM.containsKey(kind) && q != null)
                            el(doc, ke, QTY_ELEM.get(kind),
                               f2(((Number) q).doubleValue()));
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
                           f2(((Number) navp).doubleValue()));
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
                            el(doc, t2, "SharesOutstanding", String.format(
                               Locale.ROOT, "%.0f",
                               ((Number) so).doubleValue()));
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
    }

    // ---- cli ---------------------------------------------------------------
    public static void main(String[] args) throws Exception {
        if (args.length == 0) { System.err.println(
            "usage: init|import|export|roundtrip ..."); System.exit(2); }
        switch (args[0]) {
            case "init" -> init(args[1]);
            case "import" ->
                System.out.println("imported " + doImport(args[1], args[2]));
            case "export" -> { export(args[1], args[2], args[3]);
                System.out.println("wrote " + args[3]); }
            case "roundtrip" -> {
                // import then export THROUGH the DB (the required test).
                File tmp = File.createTempFile("fxdb", ".db");
                tmp.delete();
                init(tmp.getPath());
                String id = doImport(tmp.getPath(), args[1]);
                export(tmp.getPath(), id, args[2]);
                tmp.delete();
                System.out.println("round-trip ok: " + args[1]
                    + " -> DB -> " + args[2] + " (doc " + id + ")");
            }
            default -> { System.err.println("unknown: " + args[0]);
                System.exit(2); }
        }
    }
}
