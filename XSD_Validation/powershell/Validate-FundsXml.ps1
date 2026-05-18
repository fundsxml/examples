<#
.SYNOPSIS
    XSD validation in PowerShell via System.Xml.Schema.

.DESCRIPTION
    Standalone & cross-platform — resolves the official released schema
    itself (no prior tool step). Same 3-step convention as every stack:
    $env:FUNDSXML_SCHEMA_DIR (offline/corporate escape hatch) ->
    .schema-cache\ -> download from the official GitHub release
    (Invoke-WebRequest follows the 302; pulls the xmldsig-core-schema.xsd
    sibling that FundsXML 4.2.9+ imports).

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

# Nested Join-Path: the 3-arg form (-AdditionalChildPath) is PS 7+ only;
# Windows PowerShell 5.1 accepts just -Path/-ChildPath.
$repoRoot = (Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') '..')).Path
$base = "https://github.com/fundsxml/schema/releases/download/$Version"

function Get-File($url, $dest) {
    Write-Host "schema: fetch $url" -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $url -OutFile $dest -MaximumRedirection 5 -UseBasicParsing
}

if ($env:FUNDSXML_SCHEMA_DIR) {
    $schemaPath = Join-Path $env:FUNDSXML_SCHEMA_DIR 'FundsXML.xsd'
    if (-not (Test-Path $schemaPath)) {
        Write-Error "FUNDSXML_SCHEMA_DIR set but $schemaPath not found"; exit 2
    }
    Write-Host "schema: using `$FUNDSXML_SCHEMA_DIR -> $schemaPath"
}
else {
    $cacheDir   = Join-Path $repoRoot ".schema-cache/$Version"
    $schemaPath = Join-Path $cacheDir 'FundsXML.xsd'
    if (Test-Path $schemaPath) {
        Write-Host "schema: cached -> $schemaPath"
    }
    else {
        New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
        Get-File "$base/FundsXML.xsd" $schemaPath
        if (Select-String -Path $schemaPath -Pattern 'xmldsig-core-schema\.xsd' -Quiet) {
            Get-File "$base/xmldsig-core-schema.xsd" (Join-Path $cacheDir 'xmldsig-core-schema.xsd')
        }
    }
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
