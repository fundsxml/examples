// SchemaResolver — obtain the official FundsXML XSD for a version, standalone
// & cross-platform (no bash, no prior tool step; works on Windows).
//
// Same 3-step convention as the Java (XsdValidate.java) and Python
// (tools/fundsxml_schema.py) resolvers:
//
//   1. $FUNDSXML_SCHEMA_DIR — a directory holding FundsXML.xsd (+ the
//      xmldsig-core-schema.xsd sibling for 4.2.9+). Used as-is, NO network.
//      The escape hatch for locked-down corporate networks / offline use.
//   2. <cwd>/.schema-cache/<version>/FundsXML.xsd — reused if present.
//   3. download from the official GitHub release (HttpClient follows the
//      302 by default), caching into .schema-cache/<version>/; the relative
//      xmldsig-core-schema.xsd sibling is fetched only when imported (4.2.9+).
//
// The source of truth stays the official release URL — no committed catalog.
// Kept as a second file in this same project (one self-contained example),
// mirroring how the Java example inlines its resolver.

using System;
using System.IO;
using System.Net.Http;

internal static class SchemaResolver
{
    private const string ReleaseBase =
        "https://github.com/fundsxml/schema/releases/download/";

    /// <summary>Resolve FundsXML.xsd for <paramref name="version"/>.</summary>
    internal static string Resolve(string version)
    {
        // 1. Offline / corporate-network escape hatch: a hand-placed copy.
        string envDir = Environment.GetEnvironmentVariable("FUNDSXML_SCHEMA_DIR");
        if (!string.IsNullOrWhiteSpace(envDir))
        {
            string envXsd = Path.Combine(envDir, "FundsXML.xsd");
            if (!File.Exists(envXsd))
            {
                throw new FileNotFoundException(
                    $"FUNDSXML_SCHEMA_DIR set but {envXsd} not found");
            }
            Console.Error.WriteLine(
                $"schema: using $FUNDSXML_SCHEMA_DIR -> {envXsd}");
            return envXsd;
        }

        // 2. Local cache (shared by every stack, gitignored). The examples are
        //    documented to run from the repo root.
        string cacheDir = Path.Combine(
            Directory.GetCurrentDirectory(), ".schema-cache", version);
        string xsd = Path.Combine(cacheDir, "FundsXML.xsd");
        if (File.Exists(xsd))
        {
            Console.Error.WriteLine($"schema: cached -> {xsd}");
            return xsd;
        }

        // 3. Download from the official release (source of truth).
        Directory.CreateDirectory(cacheDir);
        Download($"{ReleaseBase}{version}/FundsXML.xsd", xsd);
        // From 4.2.9 on, FundsXML.xsd imports xmldsig-core-schema.xsd via a
        // relative path — it must sit next to FundsXML.xsd or the schema does
        // not compile. Fetch the sibling only when it is actually referenced.
        if (File.ReadAllText(xsd).Contains("xmldsig-core-schema.xsd"))
        {
            Download($"{ReleaseBase}{version}/xmldsig-core-schema.xsd",
                Path.Combine(cacheDir, "xmldsig-core-schema.xsd"));
        }
        return xsd;
    }

    // HttpClient follows the GitHub 302 (AllowAutoRedirect is on by default).
    private static void Download(string url, string outPath)
    {
        Console.Error.WriteLine($"schema: fetch {url}");
        using var http = new HttpClient();
        byte[] body = http.GetByteArrayAsync(url).GetAwaiter().GetResult();
        string tmp = outPath + ".part";
        File.WriteAllBytes(tmp, body);
        if (File.Exists(outPath))
        {
            File.Delete(outPath);
        }
        File.Move(tmp, outPath);
    }
}
