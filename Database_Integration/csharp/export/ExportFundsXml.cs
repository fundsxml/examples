// =============================================================================
// EXPORT  —  relational database  ->  FundsXML file  (C# / .NET, SQLite).
//
// Standalone, copy-me example of ONE direction (DB -> FundsXML). The reverse
// is a separate project, ../import/. Over-commented as documentation.
//
// DB SCHEMA  ../../ddl/schema.sql  (already populated by ../import/).
//
// RUN
//   dotnet run --project Database_Integration/csharp/import -- fx.db some.xml
//   dotnet run --project Database_Integration/csharp/export -- \
//     fx.db FUNDSXML_MULTI_1 out.xml
//
// DEPENDENCIES  Microsoft.Data.Sqlite + System.Xml (BCL).
//
// FUNDSXML NOTES
//   * No XML namespace -> plain element names.
//   * xsi:noNamespaceSchemaLocation MUST be created in the XMLSchema-instance
//     namespace (a plain SetAttribute drops the prefix and a validator then
//     rejects it) -> CreateAttribute("xsi", ..., XsiNs).
//   * Constants the model does not store (TotalAssetNature=OFFICIAL, Price
//     ActionCode=C / PriceNature=OFFICIAL) reproduced verbatim so the
//     round-trip compares equal (../../tools/xml_equiv.py, always paired with
//     XSD validation).
//   * ORDER BY the 1-based *_seq columns reproduces the original order of
//     multiple funds / portfolios / positions.
// =============================================================================
using System;
using System.Globalization;
using System.IO;
using System.Xml;
using Microsoft.Data.Sqlite;

internal static class ExportFundsXml
{
    const string SchemaUrl =
        "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd";
    const string XsiNs = "http://www.w3.org/2001/XMLSchema-instance";

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

    static XmlElement El(XmlDocument doc, XmlNode parent, string tag,
                         string? text = null)
    {
        var e = doc.CreateElement(tag);
        if (text != null) e.AppendChild(doc.CreateTextNode(text));
        parent.AppendChild(e);
        return e;
    }

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

    static int Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.Error.WriteLine(
                "usage: ExportFundsXml <db> <document_id> <out.xml>");
            return 2;
        }
        string db = args[0], docId = args[1], outPath = args[2];

        using var c = new SqliteConnection($"Data Source={db}");
        c.Open();

        var doc = new XmlDocument();
        var root = doc.CreateElement("FundsXML4");
        // Must really be in the xsi namespace, else a validator rejects it.
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

        var ws = new XmlWriterSettings
            { Indent = true, Encoding = new System.Text.UTF8Encoding(false) };
        using var w = XmlWriter.Create(outPath, ws);
        doc.Save(w);
        Console.WriteLine("wrote " + outPath);
        return 0;
    }
}
