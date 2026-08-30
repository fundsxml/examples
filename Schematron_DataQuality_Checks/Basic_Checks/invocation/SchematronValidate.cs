// Schematron validation in .NET / C# — drives the SchXslt CLI, classifies SVRL.
//
//   dotnet run --project Schematron_DataQuality_Checks/Basic_Checks/invocation \
//       -- Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch document.xml [--fail-on error|any]
// Exit: 0 = no error-role failed-assert, 1 = at least one, 2 = setup error.
//
// WHY NOT A .NET XSLT ENGINE
// basic_checks.sch uses queryBinding="xslt2". The .NET BCL only has XSLT 1.0
// (System.Xml.Xsl), and there is no Saxon-HE library on NuGet for .NET 8:
// Saxonica publishes its .NET packages (SaxonHE12Net*) as dotnet *tools*,
// SaxonCS is not on NuGet, and the third-party IKVM cross-compiles are
// experimental. So this example does what a .NET service in a mixed shop
// typically does: it runs the SchXslt CLI (a self-contained jar that bundles
// its own Saxon) as a child process and owns the result — the SVRL parsing,
// the error/warning classification and the exit-code contract are the same
// as in svrl-summary.py and the Java example. Prerequisite: a JDK on PATH
// (or $JAVA_HOME) — the same one the Maven Wrapper uses.
//
// The SchXslt CLI jar has no NuGet distribution; it is located standalone via
// $FUNDSXML_SCHXSLT_JAR or the Maven local repo (populated by the Java module).
//
// Verified with .NET SDK 8 + JDK 21/26 (also in CI): canonical sample -> 0
// errors / 12 warnings, negative fixture -> 1 error / exit 1.

using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Xml;

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
        string svrl = Path.Combine(tmp, "report.svrl");

        // java from $JAVA_HOME if set (what the Maven Wrapper honours), else PATH.
        string? javaHome = Environment.GetEnvironmentVariable("JAVA_HOME");
        string java = string.IsNullOrEmpty(javaHome) ? "java"
            : Path.Combine(javaHome, "bin", "java");

        // SchXslt CLI: -s schema, -d document, -o SVRL output. Its own exit code
        // is left at the default (0) on purpose — the classification below
        // decides, exactly like the Java example and svrl-summary.py.
        var psi = new ProcessStartInfo(java)
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        foreach (var a in new[] { "-jar", cliJar, "-s", sch, "-d", xml, "-o", svrl })
            psi.ArgumentList.Add(a);
        using (var proc = Process.Start(psi)!)
        {
            // Drain both pipes concurrently so a chatty child cannot block.
            var stdoutTask = proc.StandardOutput.ReadToEndAsync();
            string stderr = proc.StandardError.ReadToEnd();
            stdoutTask.Wait();
            proc.WaitForExit();
            if (proc.ExitCode != 0 || !File.Exists(svrl))
            {
                Console.Error.WriteLine("SchXslt CLI failed (exit "
                    + proc.ExitCode + "):\n" + stderr.Trim());
                return 2;
            }
        }

        var doc = new XmlDocument();
        doc.Load(svrl);
        var ns = new XmlNamespaceManager(doc.NameTable);
        ns.AddNamespace("svrl", Svrl);

        // Severity is the @role attribute, not the element name: this ruleset
        // raises warnings as <assert role="warning"> (=> failed-assert) and the
        // rounding checks as <report role="warning"> (=> successful-report).
        int errors = 0, warnings = 0;
        foreach (XmlElement fa in doc.SelectNodes(
                     "//svrl:failed-assert | //svrl:successful-report", ns)!)
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
}
