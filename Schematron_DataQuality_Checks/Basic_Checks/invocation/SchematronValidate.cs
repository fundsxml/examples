// Schematron validation in .NET / C# via Saxon for .NET (Saxonica SaxonHE).
//
//   # add the Saxon-HE-for-.NET package matching your TFM (see .csproj note)
//   dotnet run --project Schematron_DataQuality_Checks/Basic_Checks/invocation \
//       -- Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch document.xml
// Exit: 0 = no error-role failed-assert, 1 = at least one, 2 = setup error.
//
// basic_checks.sch uses queryBinding="xslt2"; the SaxonHE NuGet package
// supplies the XSLT 3.0 engine (resolved by `dotnet build`, standalone). The
// SchXslt pipeline stylesheets have no NuGet/.NET distribution, so they are
// reused from the SchXslt CLI jar, located via $FUNDSXML_SCHXSLT_JAR or the
// Maven local repo (see below); the whole xslt/ tree is extracted so the
// pipeline's relative imports resolve, then compile .sch -> SVRL stylesheet
// -> apply to instance -> SVRL, then classify (same logic as svrl-summary.py).
//
// NOTE: reference variant. The Java Schematron example is the verified, fully
// standalone path (Maven Wrapper). The flow here mirrors it exactly.

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

        // SchXslt has no NuGet/.NET distribution, so this (reference) .NET
        // stack locates the SchXslt CLI jar standalone, in order:
        //   1. $FUNDSXML_SCHXSLT_JAR (explicit path)
        //   2. the Maven local repo — the Java Schematron module declares
        //      name.dmaus.schxslt:cli:1.10.1, so `./mvnw -pl Schematron_
        //      DataQuality_Checks/Basic_Checks/invocation compile` populates it.
        const string schxsltVersion = "1.10.1";
        string m2 = Environment.GetEnvironmentVariable("MAVEN_REPO_LOCAL")
            ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                ".m2", "repository");
        string cliJar = Environment.GetEnvironmentVariable("FUNDSXML_SCHXSLT_JAR")
            ?? Path.Combine(m2, "name", "dmaus", "schxslt", "cli",
                schxsltVersion, $"cli-{schxsltVersion}.jar");
        if (!File.Exists(cliJar))
        {
            Console.Error.WriteLine(
                $"SchXslt jar not found at {cliJar}.\n"
                + "Set $FUNDSXML_SCHXSLT_JAR, or populate the Maven local repo "
                + "once with:\n  ./mvnw -q -pl Schematron_DataQuality_Checks/"
                + "Basic_Checks/invocation compile\n"
                + "(the Java Schematron example runs fully standalone via the "
                + "Maven Wrapper and is the verified path.)");
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
