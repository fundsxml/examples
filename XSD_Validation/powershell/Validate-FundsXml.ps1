<#
.SYNOPSIS
    XSD validation in PowerShell via System.Xml.Schema.

.DESCRIPTION
    Validates a FundsXML document against the official released schema,
    materialized locally by tools/fetch-schema.sh (handles the GitHub 302
    redirect and the relative xmldsig-core-schema.xsd import that FundsXML
    4.2.9+ requires).

    Security: the instance document is read with XmlResolver = $null and
    DtdProcessing = Prohibit to close XXE / external-entity vectors. A
    URL resolver is used only for the schema set's local relative import.

    Works in Windows PowerShell 5.1 and PowerShell 7+.

.PARAMETER Version
    FundsXML version, e.g. 4.2.9

.PARAMETER XmlFile
    Path to the FundsXML instance document.

.EXAMPLE
    pwsh XSD_Validation/powershell/Validate-FundsXml.ps1 4.2.9 `
        FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml

.OUTPUTS
    Exit code 0 = valid, 1 = invalid, 2 = usage/setup error.
#>
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$XmlFile
)

$ErrorActionPreference = 'Stop'

$repoRoot   = Resolve-Path (Join-Path $PSScriptRoot '..' '..')
$schemaPath = Join-Path $repoRoot ".schema-cache/$Version/FundsXML.xsd"

if (-not (Test-Path $schemaPath)) {
    Write-Error "schema not cached; run: tools/fetch-schema.sh $Version"
    exit 2
}

$schemas = New-Object System.Xml.Schema.XmlSchemaSet
# Needed only so the schema's relative xmldsig-core-schema.xsd import (4.2.9+)
# resolves from the same directory.
$schemas.XmlResolver = New-Object System.Xml.XmlUrlResolver
[void]$schemas.Add($null, $schemaPath)

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
    Write-Error "INVALID: $XmlFile (FundsXML $Version)"
    exit 1
}

Write-Host "VALID: $XmlFile (FundsXML $Version)"
exit 0
