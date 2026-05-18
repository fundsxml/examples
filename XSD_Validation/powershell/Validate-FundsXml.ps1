<#
.SYNOPSIS
    XSD validation in PowerShell via System.Xml.Schema.

.DESCRIPTION
    Standalone & cross-platform — you give it exactly two things: a schema
    and an XML file. <Schema> is a path to an XSD file OR a remote URL, e.g.
    the official release:
      https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
    No version, no env var, no cache, no resolver — whatever you point at is
    used as-is.

    Security: the instance document is read with XmlResolver = $null and
    DtdProcessing = Prohibit to close XXE / external-entity vectors. A URL
    resolver is used only for the schema set, so a remote schema and the
    schema's relative xmldsig-core-schema.xsd import (FundsXML 4.2.9+)
    resolve. A local schema path's xmldsig sibling, if imported, must sit
    next to it (it does in any complete copy of an official release).

    Works in Windows PowerShell 5.1 and PowerShell 7+.

.PARAMETER Schema
    Path to FundsXML.xsd, or a remote URL.

.PARAMETER XmlFile
    Path to the FundsXML instance document.

.EXAMPLE
    pwsh XSD_Validation/powershell/Validate-FundsXml.ps1 `
      https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd `
      FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml

.OUTPUTS
    Exit code 0 = valid, 1 = invalid, 2 = usage/setup error.
#>
param(
    [Parameter(Mandatory = $true)][string]$Schema,
    [Parameter(Mandatory = $true)][string]$XmlFile
)

$ErrorActionPreference = 'Stop'

$schemas = New-Object System.Xml.Schema.XmlSchemaSet
# Resolves a remote schema URL and the schema's relative
# xmldsig-core-schema.xsd import (4.2.9+) from the same location.
$schemas.XmlResolver = New-Object System.Xml.XmlUrlResolver
[void]$schemas.Add($null, $Schema)

$settings = New-Object System.Xml.XmlReaderSettings
$settings.ValidationType = [System.Xml.ValidationType]::Schema
$settings.Schemas = $schemas
$settings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
$settings.XmlResolver = $null   # harden instance document against XXE

$script:failed = $false
$handler = [System.Xml.Schema.ValidationEventHandler] {
    param($sender, $e)
    if ($e.Severity -eq [System.Xml.Schema.XmlSeverityType]::Error) {
        $script:failed = $true
        Write-Host ("  line {0}: {1}" -f $e.Exception.LineNumber, $e.Message)
    }
}
$settings.add_ValidationEventHandler($handler)

try {
    $reader = [System.Xml.XmlReader]::Create($XmlFile, $settings)
    while ($reader.Read()) { }
    $reader.Dispose()
}
catch [System.Xml.XmlException] {
    Write-Host ("  {0}" -f $_.Exception.Message)
    $script:failed = $true
}

if ($script:failed) {
    Write-Error "INVALID: $XmlFile (schema $Schema)"
    exit 1
}

Write-Host "VALID: $XmlFile (schema $Schema)"
exit 0
