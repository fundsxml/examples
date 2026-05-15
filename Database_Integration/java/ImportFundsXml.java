// =============================================================================
// IMPORT  —  FundsXML file  ->  relational database  (Java, SQLite via JDBC).
//
// Standalone, copy-me example of ONE direction (FundsXML -> DB). The reverse
// is a separate program, ExportFundsXml.java. Over-commented as documentation.
//
// DB SCHEMA  ../ddl/schema.sql  (document -> fund -> portfolio -> position;
//   share_class per fund; asset document-scoped). Creates the schema in a
//   fresh SQLite DB, then loads the file.
//
// RUN  (sqlite-jdbc fetched by tools/fetch-tools.sh into .lib/)
//   tools/fetch-tools.sh
//   CP=.lib/sqlite-jdbc-3.46.1.3.jar
//   javac -cp "$CP" -d /tmp/db Database_Integration/java/ImportFundsXml.java
//   java --enable-native-access=ALL-UNNAMED -cp "$CP:/tmp/db" \
//     ImportFundsXml fx.db FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
//
// DEPENDENCIES  org.xerial:sqlite-jdbc + the JDK. XML via native javax.xml
//   DOM/XPath — NO JAXB (a thin DOM binding is smaller and version-tolerant).
//
// FUNDSXML ASSUMPTIONS
//   * No XML namespace -> bare element names in XPath.
//   * Many <Fund>/<Portfolio>/<Position>: all iterated; 1-based *_seq columns
//     preserve order so the separate export reproduces the original document.
//   * Positions link to AssetMasterData by shared <UniqueID> -> `asset` is
//     document-scoped.
//
// SECURITY  the DOM parser forbids DOCTYPE/external entities (XXE).
// =============================================================================
import java.io.FileInputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Statement;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class ImportFundsXml {

    static final java.util.Set<String> POSITION_KINDS = java.util.Set.of(
        "Equity", "Bond", "ShareClass", "Warrant", "Certificate", "Option",
        "Future", "FXForward", "Swap", "Repo", "RealEstate", "CallMoney",
        "Account", "Generic");
    static final java.util.Map<String, String> QTY_ELEM = java.util.Map.of(
        "Equity", "Units", "Warrant", "Units", "Certificate", "Units",
        "Bond", "Nominal", "ShareClass", "Shares",
        "Option", "Contracts", "Future", "Contracts");

    static XPath xpath() { return XPathFactory.newInstance().newXPath(); }

    /** First matching descendant's text (bare names; no namespace). */
    static String t(Node ctx, String expr) throws Exception {
        Node n = (Node) xpath().evaluate(expr, ctx, XPathConstants.NODE);
        return n == null ? null : n.getTextContent();
    }
    static Double num(String s) {
        return (s == null || s.isBlank()) ? null : Double.valueOf(s.trim());
    }
    static void setNum(PreparedStatement ps, int i, Double v) throws Exception {
        if (v == null) ps.setNull(i, java.sql.Types.DECIMAL);
        else ps.setDouble(i, v);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: ImportFundsXml <db> <fundsxml.xml>");
            System.exit(2);
        }
        String db = args[0], xml = args[1];

        // ---- parse the FundsXML file (hardened) ---------------------------
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        f.setFeature("http://xml.org/sax/features/external-general-entities", false);
        f.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        f.setExpandEntityReferences(false);
        Document doc;
        try (FileInputStream in = new FileInputStream(xml)) {
            doc = f.newDocumentBuilder().parse(in);
        }
        XPath xp = xpath();

        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            c.createStatement().execute("PRAGMA foreign_keys = ON");

            // ---- create the schema (fresh DB) -----------------------------
            Path ddl = Path.of(System.getProperty("user.dir"),
                "Database_Integration", "ddl", "schema.sql");
            if (!Files.exists(ddl)) ddl = Path.of("..", "ddl", "schema.sql");
            StringBuilder clean = new StringBuilder();
            for (String line : Files.readString(ddl).split("\n")) {
                int cut = line.indexOf("--");        // strip line comments
                clean.append(cut >= 0 ? line.substring(0, cut) : line)
                     .append('\n');
            }
            try (Statement st = c.createStatement()) {
                for (String stmt : clean.toString().split(";"))
                    if (!stmt.strip().isEmpty()) st.execute(stmt);
            }

            c.setAutoCommit(false);
            Node cd = (Node) xp.evaluate("/FundsXML4/ControlData", doc,
                XPathConstants.NODE);
            String docId = t(cd, "UniqueDocumentID");

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
                int fundSeq = fi + 1;                // 1-based document order
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
            System.out.println("imported document_id: " + docId);
        }
    }
}
