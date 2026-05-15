// =============================================================================
// IMPORT  —  FundsXML file  ->  relational database  (C# / .NET, SQLite).
//
// Standalone, copy-me example of ONE direction (FundsXML -> DB). The reverse
// is a separate project, ../export/. Over-commented as documentation.
//
// DB SCHEMA  ../../ddl/schema.sql  (document -> fund -> portfolio -> position;
//   share_class per fund; asset document-scoped). Creates the schema in a
//   fresh SQLite DB, then loads the file.
//
// RUN
//   dotnet run --project Database_Integration/csharp/import -- \
//     fx.db FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
//   dotnet run --project Database_Integration/csharp/export -- \
//     fx.db FUNDSXML_MULTI_1 out.xml
//
// DEPENDENCIES  Microsoft.Data.Sqlite + System.Xml (BCL). No XSD binding.
//
// FUNDSXML ASSUMPTIONS
//   * No XML namespace -> bare element names in XPath.
//   * Many <Fund>/<Portfolio>/<Position>: all iterated; 1-based *_seq columns
//     preserve order so the separate export reproduces the original document.
//   * Positions link to AssetMasterData by shared <UniqueID> -> `asset` is
//     document-scoped.
//
// SECURITY  XmlReaderSettings: DtdProcessing.Prohibit + XmlResolver=null (XXE).
// =============================================================================
using System;
using System.Globalization;
using System.IO;
using System.Xml;
using Microsoft.Data.Sqlite;

internal static class ImportFundsXml
{
    static readonly System.Collections.Generic.HashSet<string> PositionKinds =
        new() { "Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                "Option", "Future", "FXForward", "Swap", "Repo", "RealEstate",
                "CallMoney", "Account", "Generic" };
    static readonly System.Collections.Generic.Dictionary<string, string> QtyElem =
        new() { ["Equity"] = "Units", ["Warrant"] = "Units",
                ["Certificate"] = "Units", ["Bond"] = "Nominal",
                ["ShareClass"] = "Shares", ["Option"] = "Contracts",
                ["Future"] = "Contracts" };

    static string? T(XmlNode ctx, string xpath)
    {
        var n = ctx.SelectSingleNode(xpath);
        return string.IsNullOrEmpty(n?.InnerText) ? null : n!.InnerText;
    }
    static object DbNum(string? s) =>
        string.IsNullOrWhiteSpace(s) ? DBNull.Value
            : double.Parse(s, CultureInfo.InvariantCulture);

    static void Run(SqliteConnection c, string sql, params object?[] ps)
    {
        using var cmd = c.CreateCommand();
        cmd.CommandText = sql;
        for (int i = 0; i < ps.Length; i++)
            cmd.Parameters.AddWithValue($"@p{i}", ps[i] ?? DBNull.Value);
        cmd.ExecuteNonQuery();
    }

    static string DdlPath()
    {
        foreach (var p in new[] {
                     Path.Combine("Database_Integration", "ddl", "schema.sql"),
                     Path.Combine("..", "..", "ddl", "schema.sql") })
            if (File.Exists(p)) return p;
        throw new FileNotFoundException("ddl/schema.sql not found");
    }

    static int Main(string[] args)
    {
        if (args.Length != 2)
        {
            Console.Error.WriteLine(
                "usage: ImportFundsXml <db> <fundsxml.xml>");
            return 2;
        }
        string db = args[0], xml = args[1];

        // ---- parse the FundsXML file (hardened) ---------------------------
        var settings = new XmlReaderSettings
        {
            DtdProcessing = DtdProcessing.Prohibit,
            XmlResolver = null
        };
        var doc = new XmlDocument();
        using (var r = XmlReader.Create(xml, settings)) doc.Load(r);

        using var c = new SqliteConnection($"Data Source={db}");
        c.Open();
        Run(c, "PRAGMA foreign_keys = ON");

        // ---- create the schema (fresh DB) ---------------------------------
        var sb = new System.Text.StringBuilder();
        foreach (var line in File.ReadAllLines(DdlPath()))
        {
            int cut = line.IndexOf("--", StringComparison.Ordinal);
            sb.AppendLine(cut >= 0 ? line[..cut] : line);
        }
        foreach (var stmt in sb.ToString().Split(';'))
            if (stmt.Trim().Length > 0) Run(c, stmt);

        using var tx = c.BeginTransaction();
        var cd = doc.SelectSingleNode("/FundsXML4/ControlData")!;
        var docId = T(cd, "UniqueDocumentID")!;

        Run(c, "INSERT INTO document VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7,@p8)",
            docId, T(cd, "DocumentGenerated"), T(cd, "Version"),
            T(cd, "ContentDate"), T(cd, "DataOperation"),
            T(cd, "DataSupplier/SystemCountry"), T(cd, "DataSupplier/Short"),
            T(cd, "DataSupplier/Name"), T(cd, "DataSupplier/Type"));

        var funds = doc.SelectNodes("/FundsXML4/Funds/Fund")!;
        for (int fi = 0; fi < funds.Count; fi++)
        {
            var fund = funds[fi]!;
            int fundSeq = fi + 1;                        // 1-based doc order
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

            foreach (XmlNode sc in fund.SelectNodes(
                         "SingleFund/ShareClasses/ShareClass")!)
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

        foreach (XmlNode a in doc.SelectNodes(
                     "/FundsXML4/AssetMasterData/Asset")!)
            Run(c, "INSERT INTO asset VALUES (@p0,@p1,@p2,@p3,@p4,@p5,@p6)",
                docId, T(a, "UniqueID"), T(a, "Identifiers/ISIN"),
                T(a, "Name"), T(a, "AssetType"), T(a, "Currency"),
                T(a, "Country"));

        tx.Commit();
        Console.WriteLine("imported document_id: " + docId);
        return 0;
    }
}
