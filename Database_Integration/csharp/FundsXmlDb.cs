// =============================================================================
// FundsXML <-> relational database — runnable reference (C# / .NET, SQLite).
//
// PURPOSE
//   Standalone, copy-me example of BOTH directions (import a FundsXML file into
//   the relational schema, export it back). Over-commented on purpose so it
//   doubles as documentation for your own implementation.
//
// DB SCHEMA  ../ddl/schema.sql  (document -> fund -> portfolio -> position;
//   share_class per fund; asset document-scoped).
//
// RUN
//   dotnet run --project Database_Integration/csharp -- \
//     roundtrip FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml out.xml
//   commands: init <db> | import <db> <xml> | export <db> <docId> <out> |
//             roundtrip <xml> <out>
//
// DEPENDENCIES
//   Microsoft.Data.Sqlite (bundles native SQLite) + System.Xml in the BCL.
//   No XSD data-binding: System.Xml DOM/XPath keeps it small and
//   version-tolerant (FundsXML 4.x is backward compatible).
//
// FUNDSXML ASSUMPTIONS
//   * No XML namespace -> bare element names in XPath.
//   * Many <Fund>/<Portfolio>/<Position>: all iterated; 1-based *_seq columns
//     preserve order so the round-trip compares equal (../tools/xml_equiv.py).
//   * Positions link to AssetMasterData by shared <UniqueID> -> `asset` is
//     document-scoped.
//   * Export normalized to the 4.2.9 schema URL; constants the model does not
//     store (TotalAssetNature=OFFICIAL, Price ActionCode=C / PriceNature=
//     OFFICIAL) are reproduced verbatim.
//
// SECURITY
//   XmlReaderSettings: DtdProcessing.Prohibit + XmlResolver=null  (no XXE).
// =============================================================================
using System;
using System.Globalization;
using System.IO;
using System.Xml;
using Microsoft.Data.Sqlite;

internal static class FundsXmlDb
{
    const string SchemaUrl =
        "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd";

    // Position instrument-class element + its mandatory quantity child.
    static readonly System.Collections.Generic.HashSet<string> PositionKinds =
        new() { "Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                "Option", "Future", "FXForward", "Swap", "Repo", "RealEstate",
                "CallMoney", "Account", "Generic" };
    static readonly System.Collections.Generic.Dictionary<string, string> QtyElem =
        new() { ["Equity"] = "Units", ["Warrant"] = "Units",
                ["Certificate"] = "Units", ["Bond"] = "Nominal",
                ["ShareClass"] = "Shares", ["Option"] = "Contracts",
                ["Future"] = "Contracts" };

    static string Inv(double v) => v.ToString("0.00", CultureInfo.InvariantCulture);

    // ---- helpers -----------------------------------------------------------
    static string? T(XmlNode ctx, string xpath)
    {
        var n = ctx.SelectSingleNode(xpath);
        return string.IsNullOrEmpty(n?.InnerText) ? null : n!.InnerText;
    }

    static object DbNum(string? s) =>
        string.IsNullOrWhiteSpace(s) ? DBNull.Value
            : double.Parse(s, CultureInfo.InvariantCulture);

    static XmlElement El(XmlDocument doc, XmlNode parent, string tag,
                         string? text = null)
    {
        var e = doc.CreateElement(tag);
        if (text != null) e.AppendChild(doc.CreateTextNode(text));
        parent.AppendChild(e);
        return e;
    }

    static SqliteConnection Open(string db)
    {
        var c = new SqliteConnection($"Data Source={db}");
        c.Open();
        using var pragma = c.CreateCommand();
        pragma.CommandText = "PRAGMA foreign_keys = ON";
        pragma.ExecuteNonQuery();
        return c;
    }

    static void Exec(SqliteConnection c, string sql)
    {
        using var cmd = c.CreateCommand();
        cmd.CommandText = sql;
        cmd.ExecuteNonQuery();
    }

    // Bind helper: positional @p0,@p1,... mirrors the other languages' "?".
    static void Run(SqliteConnection c, string sql, params object?[] ps)
    {
        using var cmd = c.CreateCommand();
        cmd.CommandText = sql;
        for (int i = 0; i < ps.Length; i++)
            cmd.Parameters.AddWithValue($"@p{i}", ps[i] ?? DBNull.Value);
        cmd.ExecuteNonQuery();
    }

    static XmlDocument ParseSecure(string xml)
    {
        var settings = new XmlReaderSettings
        {
            DtdProcessing = DtdProcessing.Prohibit, // reject DOCTYPE (XXE)
            XmlResolver = null                      // no external entities
        };
        var doc = new XmlDocument();
        using var r = XmlReader.Create(xml, settings);
        doc.Load(r);
        return doc;
    }

    static string DdlPath()
    {
        // Works whether run from repo root or the csharp/ project dir.
        foreach (var p in new[] { Path.Combine("Database_Integration", "ddl",
                     "schema.sql"), Path.Combine("..", "ddl", "schema.sql") })
            if (File.Exists(p)) return p;
        throw new FileNotFoundException("ddl/schema.sql not found");
    }

    static void Init(string db)
    {
        // Strip "--" line comments (no string literals in the DDL) then run
        // each ";"-separated statement.
        var lines = File.ReadAllLines(DdlPath());
        var sb = new System.Text.StringBuilder();
        foreach (var line in lines)
        {
            int cut = line.IndexOf("--", StringComparison.Ordinal);
            sb.AppendLine(cut >= 0 ? line[..cut] : line);
        }
        using var c = Open(db);
        foreach (var stmt in sb.ToString().Split(';'))
            if (stmt.Trim().Length > 0) Exec(c, stmt);
    }

    // ---- import : FundsXML -> rows -----------------------------------------
    static string DoImport(string db, string xml)
    {
        var doc = ParseSecure(xml);
        var cd = doc.SelectSingleNode("/FundsXML4/ControlData")!;
        var docId = T(cd, "UniqueDocumentID")!;

        using var c = Open(db);
        using var tx = c.BeginTransaction();

        Run(c, "INSERT INTO document VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7,@p8)",
            docId, T(cd, "DocumentGenerated"), T(cd, "Version"),
            T(cd, "ContentDate"), T(cd, "DataOperation"),
            T(cd, "DataSupplier/SystemCountry"), T(cd, "DataSupplier/Short"),
            T(cd, "DataSupplier/Name"), T(cd, "DataSupplier/Type"));

        var funds = doc.SelectNodes("/FundsXML4/Funds/Fund")!;
        for (int fi = 0; fi < funds.Count; fi++)
        {
            var fund = funds[fi]!;
            int fundSeq = fi + 1;                       // 1-based doc order
            var ccy = T(fund, "Currency")!;
            var tav = fund.SelectSingleNode(
                "FundDynamicData/TotalAssetValues/TotalAssetValue")!;
            Run(c, "INSERT INTO fund VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7)",
                docId, fundSeq, T(fund, "Identifiers/LEI"),
                T(fund, "Names/OfficialName"), ccy,
                T(fund, "SingleFundFlag"), T(tav, "NavDate"),
                double.Parse(T(tav,
                    $"TotalNetAssetValue/Amount[@ccy='{ccy}']")!,
                    CultureInfo.InvariantCulture));

            var scs = fund.SelectNodes("SingleFund/ShareClasses/ShareClass")!;
            foreach (XmlNode sc in scs)
                Run(c, "INSERT INTO share_class VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7)",
                    docId, fundSeq, T(sc, "Identifiers/ISIN"),
                    T(sc, "Names/OfficialName"), T(sc, "Currency"),
                    DbNum(T(sc, "Prices/Price/NavPrice")),
                    DbNum(T(sc, $"TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy='{ccy}']")),
                    DbNum(T(sc, "TotalAssetValues/TotalAssetValue/SharesOutstanding")));

            var ports = fund.SelectNodes(
                "FundDynamicData/Portfolios/Portfolio")!;
            for (int pi = 0; pi < ports.Count; pi++)
            {
                var port = ports[pi]!;
                int portSeq = pi + 1;
                Run(c, "INSERT INTO portfolio VALUES (@p0,@p1,@p2,@p3)",
                    docId, fundSeq, portSeq, T(port, "NavDate"));
                var poss = port.SelectNodes("Positions/Position")!;
                for (int qi = 0; qi < poss.Count; qi++)
                {
                    var pos = poss[qi]!;
                    string? kind = null;
                    foreach (XmlNode ch in pos.ChildNodes)
                        if (ch.NodeType == XmlNodeType.Element
                            && PositionKinds.Contains(ch.Name))
                        { kind = ch.Name; break; }
                    object qty = (kind != null && QtyElem.ContainsKey(kind))
                        ? DbNum(T(pos, $"{kind}/{QtyElem[kind]}"))
                        : DBNull.Value;
                    Run(c, "INSERT INTO position VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7,@p8,@p9,@p10)",
                        docId, fundSeq, portSeq, qi + 1,
                        T(pos, "UniqueID"), T(pos, "Identifiers/ISIN"),
                        T(pos, "Currency"),
                        double.Parse(T(pos, $"TotalValue/Amount[@ccy='{ccy}']")!,
                            CultureInfo.InvariantCulture),
                        double.Parse(T(pos, "TotalPercentage")!,
                            CultureInfo.InvariantCulture),
                        kind, qty);
                }
            }
        }

        var assets = doc.SelectNodes("/FundsXML4/AssetMasterData/Asset")!;
        foreach (XmlNode a in assets)
            Run(c, "INSERT INTO asset VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6)",
                docId, T(a, "UniqueID"), T(a, "Identifiers/ISIN"),
                T(a, "Name"), T(a, "AssetType"), T(a, "Currency"),
                T(a, "Country"));

        tx.Commit();
        return docId;
    }

    // ---- export : rows -> FundsXML ----------------------------------------
    static SqliteDataReader Q(SqliteConnection c, string sql,
                              params object?[] ps)
    {
        var cmd = c.CreateCommand();
        cmd.CommandText = sql;
        for (int i = 0; i < ps.Length; i++)
            cmd.Parameters.AddWithValue($"@p{i}", ps[i] ?? DBNull.Value);
        return cmd.ExecuteReader();
    }

    static string? S(SqliteDataReader r, string col) =>
        r.IsDBNull(r.GetOrdinal(col)) ? null : r.GetString(r.GetOrdinal(col));
    static double D(SqliteDataReader r, string col) =>
        Convert.ToDouble(r.GetValue(r.GetOrdinal(col)),
            CultureInfo.InvariantCulture);
    static bool Null(SqliteDataReader r, string col) =>
        r.IsDBNull(r.GetOrdinal(col));

    static void Export(string db, string docId, string outPath)
    {
        using var c = Open(db);
        var doc = new XmlDocument();
        var root = doc.CreateElement("FundsXML4");
        // xsi:noNamespaceSchemaLocation must really live in the
        // XMLSchema-instance namespace, otherwise a validator rejects it
        // ("attribute 'noNamespaceSchemaLocation' is not allowed"). Create it
        // as a properly namespaced attribute (this also emits xmlns:xsi).
        const string XsiNs = "http://www.w3.org/2001/XMLSchema-instance";
        var sl = doc.CreateAttribute("xsi", "noNamespaceSchemaLocation", XsiNs);
        sl.Value = SchemaUrl;
        root.Attributes.Append(sl);
        doc.AppendChild(root);

        using (var d = Q(c, "SELECT * FROM document WHERE document_id=@p0",
                   docId))
        {
            if (!d.Read()) throw new Exception($"no document {docId}");
            var cd = El(doc, root, "ControlData");
            El(doc, cd, "UniqueDocumentID", S(d, "document_id"));
            // Regenerate timestamp; xml_equiv.py ignores its value.
            El(doc, cd, "DocumentGenerated",
                S(d, "generated") ?? "2025-10-02T00:00:00");
            if (!Null(d, "version"))                 // none for 4.0.0
                El(doc, cd, "Version", S(d, "version"));
            El(doc, cd, "ContentDate", S(d, "content_date"));
            var ds = El(doc, cd, "DataSupplier");
            El(doc, ds, "SystemCountry", S(d, "supplier_country"));
            El(doc, ds, "Short", S(d, "supplier_short"));
            El(doc, ds, "Name", S(d, "supplier_name"));
            El(doc, ds, "Type", S(d, "supplier_type"));
            El(doc, cd, "DataOperation", S(d, "data_operation"));
        }

        var fundsEl = El(doc, root, "Funds");
        var fundRows = new System.Collections.Generic.List<
            System.Collections.Generic.Dictionary<string, object?>>();
        using (var fr = Q(c, "SELECT * FROM fund WHERE document_id=@p0 "
                   + "ORDER BY fund_seq", docId))
            while (fr.Read())
                fundRows.Add(new() {
                    ["fund_seq"] = fr.GetInt32(fr.GetOrdinal("fund_seq")),
                    ["currency"] = S(fr, "currency"),
                    ["lei"] = S(fr, "lei"),
                    ["official_name"] = S(fr, "official_name"),
                    ["single_fund_flag"] = S(fr, "single_fund_flag"),
                    ["nav_date"] = S(fr, "nav_date"),
                    ["total_nav"] = D(fr, "total_nav") });

        foreach (var f in fundRows)
        {
            var ccy = (string)f["currency"]!;
            int fundSeq = (int)f["fund_seq"]!;
            var navDate = (string?)f["nav_date"];
            var fund = El(doc, fundsEl, "Fund");
            if (f["lei"] != null)
                El(doc, El(doc, fund, "Identifiers"), "LEI",
                   (string?)f["lei"]);
            El(doc, El(doc, fund, "Names"), "OfficialName",
               (string?)f["official_name"]);
            El(doc, fund, "Currency", ccy);
            if (f["single_fund_flag"] != null)
                El(doc, fund, "SingleFundFlag",
                   (string?)f["single_fund_flag"]);

            var fdd = El(doc, fund, "FundDynamicData");
            var tavp = El(doc, El(doc, fdd, "TotalAssetValues"),
                "TotalAssetValue");
            El(doc, tavp, "NavDate", navDate);
            El(doc, tavp, "TotalAssetNature", "OFFICIAL");
            var amt = El(doc, El(doc, tavp, "TotalNetAssetValue"), "Amount",
                Inv((double)f["total_nav"]!));
            amt.SetAttribute("ccy", ccy);

            var ports = El(doc, fdd, "Portfolios");
            var portRows = new System.Collections.Generic.List<(int seq,
                string? nav)>();
            using (var pr = Q(c, "SELECT portfolio_seq,nav_date FROM portfolio"
                       + " WHERE document_id=@p0 AND fund_seq=@p1 ORDER BY "
                       + "portfolio_seq", docId, fundSeq))
                while (pr.Read())
                    portRows.Add((pr.GetInt32(0),
                        pr.IsDBNull(1) ? null : pr.GetString(1)));
            foreach (var (pseq, pnav) in portRows)
            {
                var pe = El(doc, ports, "Portfolio");
                El(doc, pe, "NavDate", pnav);
                var poss = El(doc, pe, "Positions");
                var posRows = new System.Collections.Generic.List<
                    System.Collections.Generic.Dictionary<string, object?>>();
                using (var qr = Q(c, "SELECT * FROM position WHERE "
                           + "document_id=@p0 AND fund_seq=@p1 AND "
                           + "portfolio_seq=@p2 ORDER BY position_seq",
                           docId, fundSeq, pseq))
                    while (qr.Read())
                        posRows.Add(new() {
                            ["unique_id"] = S(qr, "unique_id"),
                            ["isin"] = S(qr, "isin"),
                            ["currency"] = S(qr, "currency"),
                            ["value"] = D(qr, "value_fund_ccy"),
                            ["pct"] = D(qr, "percentage"),
                            ["kind"] = S(qr, "kind"),
                            ["qty"] = Null(qr, "kind_qty")
                                ? (object?)null : D(qr, "kind_qty") });
                foreach (var p in posRows)
                {
                    var pos = El(doc, poss, "Position");
                    El(doc, pos, "UniqueID", (string?)p["unique_id"]);
                    if (p["isin"] != null)
                        El(doc, El(doc, pos, "Identifiers"), "ISIN",
                           (string?)p["isin"]);
                    if (p["currency"] != null)
                        El(doc, pos, "Currency", (string?)p["currency"]);
                    var tv = El(doc, El(doc, pos, "TotalValue"), "Amount",
                        Inv((double)p["value"]!));
                    tv.SetAttribute("ccy", ccy);
                    El(doc, pos, "TotalPercentage", Inv((double)p["pct"]!));
                    var kind = p["kind"] is string k
                        && PositionKinds.Contains(k) ? k : "Generic";
                    var ke = El(doc, pos, kind);
                    if (QtyElem.ContainsKey(kind) && p["qty"] != null)
                        El(doc, ke, QtyElem[kind], Inv((double)p["qty"]!));
                }
            }

            var scRows = new System.Collections.Generic.List<
                System.Collections.Generic.Dictionary<string, object?>>();
            using (var sr = Q(c, "SELECT * FROM share_class WHERE "
                       + "document_id=@p0 AND fund_seq=@p1 ORDER BY isin",
                       docId, fundSeq))
                while (sr.Read())
                    scRows.Add(new() {
                        ["isin"] = S(sr, "isin"),
                        ["official_name"] = S(sr, "official_name"),
                        ["currency"] = S(sr, "currency"),
                        ["nav_price"] = Null(sr, "nav_price")
                            ? (object?)null : D(sr, "nav_price"),
                        ["nav_fund_ccy"] = Null(sr, "nav_fund_ccy")
                            ? (object?)null : D(sr, "nav_fund_ccy"),
                        ["shares"] = Null(sr, "shares_outstanding")
                            ? (object?)null : D(sr, "shares_outstanding") });
            if (scRows.Count > 0)
            {
                var sce = El(doc, El(doc, fund, "SingleFund"),
                    "ShareClasses");
                foreach (var sc in scRows)
                {
                    var x = El(doc, sce, "ShareClass");
                    El(doc, El(doc, x, "Identifiers"), "ISIN",
                       (string?)sc["isin"]);
                    if (sc["official_name"] != null)
                        El(doc, El(doc, x, "Names"), "OfficialName",
                           (string?)sc["official_name"]);
                    El(doc, x, "Currency", (string?)sc["currency"]);
                    if (sc["nav_price"] != null)
                    {
                        var pr2 = El(doc, El(doc, x, "Prices"), "Price");
                        El(doc, pr2, "ActionCode", "C");
                        El(doc, pr2, "NavDate", navDate);
                        El(doc, pr2, "PriceCurrency",
                           (string?)sc["currency"]);
                        El(doc, pr2, "PriceNature", "OFFICIAL");
                        El(doc, pr2, "NavPrice",
                           Inv((double)sc["nav_price"]!));
                    }
                    if (sc["nav_fund_ccy"] != null)
                    {
                        var t2 = El(doc, El(doc, x, "TotalAssetValues"),
                            "TotalAssetValue");
                        El(doc, t2, "NavDate", navDate);
                        El(doc, t2, "TotalAssetNature", "OFFICIAL");
                        var a2 = El(doc, El(doc, t2, "TotalNetAssetValue"),
                            "Amount", Inv((double)sc["nav_fund_ccy"]!));
                        a2.SetAttribute("ccy", ccy);
                        if (sc["shares"] != null)
                            El(doc, t2, "SharesOutstanding",
                               ((double)sc["shares"]!).ToString("0",
                                   CultureInfo.InvariantCulture));
                    }
                }
            }
        }

        var assetRows = new System.Collections.Generic.List<
            System.Collections.Generic.Dictionary<string, string?>>();
        using (var ar = Q(c, "SELECT * FROM asset WHERE document_id=@p0 "
                   + "ORDER BY unique_id", docId))
            while (ar.Read())
                assetRows.Add(new() {
                    ["unique_id"] = S(ar, "unique_id"),
                    ["isin"] = S(ar, "isin"),
                    ["currency"] = S(ar, "currency"),
                    ["country"] = S(ar, "country"),
                    ["name"] = S(ar, "name"),
                    ["asset_type"] = S(ar, "asset_type") });
        if (assetRows.Count > 0)
        {
            var amd = El(doc, root, "AssetMasterData");
            foreach (var a in assetRows)
            {
                var ae = El(doc, amd, "Asset");
                El(doc, ae, "UniqueID", a["unique_id"]);
                if (a["isin"] != null)
                    El(doc, El(doc, ae, "Identifiers"), "ISIN", a["isin"]);
                El(doc, ae, "Currency", a["currency"]);
                if (a["country"] != null)
                    El(doc, ae, "Country", a["country"]);
                El(doc, ae, "Name", a["name"]);
                El(doc, ae, "AssetType", a["asset_type"]);
            }
        }

        var settings = new XmlWriterSettings
            { Indent = true, Encoding = new System.Text.UTF8Encoding(false) };
        using var w = XmlWriter.Create(outPath, settings);
        doc.Save(w);
    }

    static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("usage: init|import|export|roundtrip ...");
            return 2;
        }
        switch (args[0])
        {
            case "init":
                Init(args[1]);
                break;
            case "import":
                Console.WriteLine("imported " + DoImport(args[1], args[2]));
                break;
            case "export":
                Export(args[1], args[2], args[3]);
                Console.WriteLine("wrote " + args[3]);
                break;
            case "roundtrip":
            {
                // import then export THROUGH the DB (the required test).
                var tmp = Path.GetTempFileName();
                File.Delete(tmp);
                Init(tmp);
                var id = DoImport(tmp, args[1]);
                Export(tmp, id, args[2]);
                File.Delete(tmp);
                Console.WriteLine($"round-trip ok: {args[1]} -> DB -> "
                    + $"{args[2]} (doc {id})");
                break;
            }
            default:
                Console.Error.WriteLine("unknown: " + args[0]);
                return 2;
        }
        return 0;
    }
}
