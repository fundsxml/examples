// XSD validation in .NET / C# via System.Xml.Schema.
//
// Run as a single-file program (no project needed) with the .NET SDK:
//   dotnet run --project XSD_Validation/dotnet -- <version> <xml-file>
// or compile XsdValidate.cs into any console app. Exit: 0 valid, 1 invalid,
// 2 usage/setup error.
//
// Validates against the official released schema, materialized locally by
// tools/fetch-schema.sh (handles the GitHub 302 redirect and the relative
// xmldsig-core-schema.xsd import that FundsXML 4.2.9+ requires).
//
// Security: XmlResolver = null on the reader closes XXE / external-entity
// vectors. An XmlUrlResolver is used ONLY to resolve the schema set's local
// relative xmldsig import, never for instance documents.

using System;
using System.IO;
using System.Xml;
using System.Xml.Schema;

internal static class XsdValidate
{
    private static int Main(string[] args)
    {
        if (args.Length != 2)
        {
            Console.Error.WriteLine("usage: XsdValidate <version> <xml-file>");
            return 2;
        }

        string version = args[0];
        string xmlFile = args[1];

        string repoRoot = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
        string schemaPath = Path.Combine(
            repoRoot, ".schema-cache", version, "FundsXML.xsd");

        if (!File.Exists(schemaPath))
        {
            Console.Error.WriteLine(
                $"schema not cached; run: tools/fetch-schema.sh {version}");
            return 2;
        }

        var schemas = new XmlSchemaSet
        {
            // Needed only so the schema's relative xmldsig-core-schema.xsd
            // import (4.2.9+) resolves from the same directory.
            XmlResolver = new XmlUrlResolver()
        };
        schemas.Add(null, schemaPath);

        bool failed = false;
        var settings = new XmlReaderSettings
        {
            ValidationType = ValidationType.Schema,
            Schemas = schemas,
            DtdProcessing = DtdProcessing.Prohibit,
            XmlResolver = null // harden the instance document against XXE
        };
        settings.ValidationFlags |= XmlSchemaValidationFlags.ReportValidationWarnings;
        settings.ValidationEventHandler += (_, e) =>
        {
            if (e.Severity == XmlSeverityType.Error)
            {
                failed = true;
                Console.Error.WriteLine(
                    $"  line {e.Exception.LineNumber}: {e.Message}");
            }
        };

        try
        {
            using var reader = XmlReader.Create(xmlFile, settings);
            while (reader.Read()) { }
        }
        catch (XmlException ex)
        {
            Console.Error.WriteLine($"  {ex.Message}");
            failed = true;
        }

        if (failed)
        {
            Console.Error.WriteLine(
                $"INVALID: {xmlFile} (FundsXML {version})");
            return 1;
        }

        Console.WriteLine($"VALID: {xmlFile} (FundsXML {version})");
        return 0;
    }
}
