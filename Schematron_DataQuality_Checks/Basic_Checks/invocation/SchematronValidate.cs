// Schematron validation in .NET / C# via Saxon for .NET (Saxonica SaxonHE).
//
//   dotnet add package SaxonHE        # Saxon 12.x for .NET
//   dotnet run --project Schematron_DataQuality_Checks/Basic_Checks/invocation \
//       -- ../basic_checks.sch document.xml
// Exit: 0 = no error-role failed-assert, 1 = at least one, 2 = setup error.
//
// basic_checks.sch uses queryBinding="xslt2"; Saxon supplies the XSLT 3.0
// engine. The SchXslt pipeline stylesheets are reused from the SchXslt CLI jar
// (this .NET stack resolves it via NuGet once migrated; the Java example
// already runs standalone via the Maven Wrapper): the whole xslt/ tree is extracted so
// the pipeline's relative imports resolve, then compile .sch -> SVRL stylesheet
// -> apply to instance -> SVRL, then classify (same logic as svrl-summary.py).
//
// NOTE: reference implementation — not executed in this environment (no .NET
// SDK). The flow mirrors the verified Python/CLI paths exactly.

using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Xml;
using Saxon.Api;

internal static class SchematronValidate
{
    private const string Svrl = "http://purl.oclc.org/dsdl/svrl";

    private static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine(
                "usage: SchematronValidate <schema.sch> <xml-file> [--fail-on error|any]");
            return 2;
        }
        string sch = args[0], xml = args[1];
        string failOn = args.SkipWhile(a => a != "--fail-on")
                            .Skip(1).FirstOrDefault() ?? "error";

        string repoRoot = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "..", ".."));
        string cliJar = Path.Combine(repoRoot, ".lib", "schxslt-cli-1.10.1.jar");
        if (!File.Exists(cliJar))
        {
            Console.Error.WriteLine(
                "SchXslt jar missing (this .NET stack is migrated to NuGet in "
                + "a later phase; the Java example already runs standalone via "
                + "the Maven Wrapper)");
            return 2;
        }

        string tmp = Directory.CreateTempSubdirectory().FullName;
        using (var zip = ZipFile.OpenRead(cliJar))
            foreach (var e in zip.Entries.Where(e => e.FullName.StartsWith("xslt/")
                                                     && !e.FullName.EndsWith("/")))
            {
                string dest = Path.Combine(tmp, e.FullName);
                Directory.CreateDirectory(Path.GetDirectoryName(dest)!);
                e.ExtractToFile(dest, true);
            }

        var processor = new Processor(false);
        var comp = processor.NewXsltCompiler();

        string compiled = Path.Combine(tmp, "compiled.xsl");
        string svrl = Path.Combine(tmp, "report.svrl");

        // 1) Schematron -> SVRL stylesheet
        Transform(comp, Path.Combine(tmp, "xslt/2.0/pipeline-for-svrl.xsl"),
                  sch, compiled, processor);
        // 2) instance -> SVRL
        Transform(comp, compiled, xml, svrl, processor);

        var doc = new XmlDocument();
        doc.Load(svrl);
        var ns = new XmlNamespaceManager(doc.NameTable);
        ns.AddNamespace("svrl", Svrl);

        int errors = 0, warnings = 0;
        foreach (XmlElement fa in doc.SelectNodes("//svrl:failed-assert", ns)!)
        {
            string role = fa.GetAttribute("role").ToLowerInvariant();
            string text = (fa.SelectSingleNode("svrl:text", ns)?.InnerText ?? "")
                          .Trim();
            if (role == "error") { errors++; Console.WriteLine("ERROR   " + text); }
            else { warnings++; Console.WriteLine("WARNING " + text); }
        }
        Console.WriteLine($"\nsummary: {errors} error(s), {warnings} warning(s)");

        if (failOn == "any" && (errors > 0 || warnings > 0)) return 1;
        return errors > 0 ? 1 : 0;
    }

    private static void Transform(XsltCompiler comp, string xsl, string src,
                                  string outFile, Processor p)
    {
        var exe = comp.Compile(new Uri(Path.GetFullPath(xsl)));
        var t = exe.Load30();
        using var os = File.Create(outFile);
        t.Transform(new Uri(Path.GetFullPath(src)),
                    p.NewSerializer(os));
    }
}
