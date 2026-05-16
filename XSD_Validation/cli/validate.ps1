<#
.SYNOPSIS
  XSD validation from the command line on Windows — the counterpart of
  validate.sh. Standalone: resolves the official schema itself (no prior step).

.DESCRIPTION
  Same 3-step convention as every other stack:
    1. $env:FUNDSXML_SCHEMA_DIR — a dir with FundsXML.xsd (+ the xmldsig
       sibling for 4.2.9+). Used as-is, NO network (offline / corporate
       escape hatch).
    2. .schema-cache\<version>\FundsXML.xsd — reused if present.
    3. download from the official GitHub release (Invoke-WebRequest follows
       the 302), caching into .schema-cache\; the relative
       xmldsig-core-schema.xsd sibling is fetched only when imported (4.2.9+).

  Validation uses xmllint when it is on PATH, otherwise the built-in .NET
  System.Xml.Schema (always available on Windows) — so no extra tool to
  install. Works in Windows PowerShell 5.1 and PowerShell 7+.

.PARAMETER Version   FundsXML version, e.g. 4.2.9
.PARAMETER XmlFile   the instance document to validate
.EXAMPLE
  pwsh XSD_Validation/cli/validate.ps1 4.2.9 FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)] [string] $Version,
  [Parameter(Mandatory = $true, Position = 1)] [string] $XmlFile
)
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$base = "https://github.com/fundsxml/schema/releases/download/$Version"

function Get-File($url, $dest) {
  Write-Host "schema: fetch $url" -ForegroundColor DarkGray
  Invoke-WebRequest -Uri $url -OutFile $dest -MaximumRedirection 5 -UseBasicParsing
}

if ($env:FUNDSXML_SCHEMA_DIR) {
  $schema = Join-Path $env:FUNDSXML_SCHEMA_DIR 'FundsXML.xsd'
  if (-not (Test-Path $schema)) {
    Write-Error "FUNDSXML_SCHEMA_DIR set but $schema not found"; exit 2
  }
  Write-Host "schema: using `$FUNDSXML_SCHEMA_DIR -> $schema"
}
else {
  $cacheDir = Join-Path $repoRoot ".schema-cache\$Version"
  $schema = Join-Path $cacheDir 'FundsXML.xsd'
  if (Test-Path $schema) {
    Write-Host "schema: cached -> $schema"
  }
  else {
    New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
    Get-File "$base/FundsXML.xsd" $schema
    if (Select-String -Path $schema -Pattern 'xmldsig-core-schema\.xsd' -Quiet) {
      Get-File "$base/xmldsig-core-schema.xsd" (Join-Path $cacheDir 'xmldsig-core-schema.xsd')
    }
  }
}

$xmllint = Get-Command xmllint -ErrorAction SilentlyContinue
if ($xmllint) {
  & $xmllint.Source --noout --nonet --schema $schema $XmlFile
  if ($LASTEXITCODE -eq 0) { Write-Host "VALID: $XmlFile (FundsXML $Version)"; exit 0 }
  Write-Error "INVALID: $XmlFile (FundsXML $Version)"; exit 1
}

# No xmllint: validate with the built-in .NET schema validator. The schema set
# gets a URL resolver only so the relative xmldsig import resolves; the
# instance document is read with no resolver (XXE-hardened).
Add-Type -AssemblyName System.Xml
$set = New-Object System.Xml.Schema.XmlSchemaSet
$set.XmlResolver = New-Object System.Xml.XmlUrlResolver
[void]$set.Add($null, $schema)
$rs = New-Object System.Xml.XmlReaderSettings
$rs.ValidationType = [System.Xml.ValidationType]::Schema
$rs.Schemas = $set
$rs.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
$rs.XmlResolver = $null
$script:bad = $false
$handler = [System.Xml.Schema.ValidationEventHandler] {
  param($s, $e)
  if ($e.Severity -eq [System.Xml.Schema.XmlSeverityType]::Error) {
    $script:bad = $true
    Write-Host ("  " + $e.Message)
  }
}
$rs.add_ValidationEventHandler($handler)
try {
  $r = [System.Xml.XmlReader]::Create($XmlFile, $rs)
  while ($r.Read()) { }
  $r.Close()
}
catch { $script:bad = $true; Write-Host ("  " + $_.Exception.Message) }
if ($script:bad) { Write-Error "INVALID: $XmlFile (FundsXML $Version)"; exit 1 }
Write-Host "VALID: $XmlFile (FundsXML $Version)"
exit 0
