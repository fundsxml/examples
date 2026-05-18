// XSD validation in .NET / C# via System.Xml.Schema.
//
// Standalone & cross-platform (no bash, no prior tool step) with the .NET SDK,
// run from the repo root:
//   dotnet run --project XSD_Validation/dotnet -- <schema> <xml-file>
// Exit: 0 valid, 1 invalid, 2 usage/setup error.
//
// You give it exactly two things: the schema and the instance. <schema> is a
// path to an XSD file OR a remote URL, e.g. the official release:
//   https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
// No version, no env var, no cache, no resolver — whatever you point at is
// used as-is. For FundsXML 4.2.9+ the schema imports xmldsig-core-schema.xsd
// via a relative path, so that sibling must be reachable next to <schema>
// (it is, in the official release directory and in any complete local copy).
//
// Security: XmlResolver = null on the instance reader closes XXE / external-
// entity vectors. An XmlUrlResolver is used ONLY for the schema set, so a
// remote schema and the schema's relative xmldsig import resolve — never for
// instance documents.

using System;
using System.Xml;
using System.Xml.Schema;

internal static class XsdValidate
{
    private static int Main(string[] args)
    {
        if (args.Length != 2)
        {
            Console.Error.WriteLine("usage: XsdValidate <schema> <xml-file>");
            return 2;
        }

        string schemaArg = args[0];
        string xmlFile = args[1];

        var schemas = new XmlSchemaSet
        {
            // Resolves a remote schema URL and the schema's relative
            // xmldsig-core-schema.xsd import (4.2.9+) from the same location.
            XmlResolver = new XmlUrlResolver()
        };
        try
        {
            schemas.Add(null, schemaArg);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"schema load failed: {ex.Message}");
            return 2;
        }

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
                $"INVALID: {xmlFile} (schema {schemaArg})");
            return 1;
        }

        Console.WriteLine($"VALID: {xmlFile} (schema {schemaArg})");
        return 0;
    }
}
