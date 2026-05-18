<#
.SYNOPSIS
  XSD validation from the command line on Windows — the counterpart of
  validate.sh. You give it exactly two things: a schema and an XML file.

.DESCRIPTION
  <Schema> is a path to an XSD file OR a remote URL, e.g. the official
  release:
    https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
  No version, no env var, no cache — whatever you point at is used as-is.

  Validation uses xmllint when it is on PATH (with --nonet for XXE / external-
  entity hardening), otherwise the built-in .NET System.Xml.Schema (always
  available on Windows) — so no extra tool to install. To keep the xmllint
  hardening while still accepting a remote schema, a URL schema (and the
  relative xmldsig-core-schema.xsd sibling FundsXML 4.2.9+ imports) is fetched
  into a temp dir first, then validated offline. The .NET fallback takes a
  path or URL directly (its schema-set URL resolver handles the import).
  A local schema path's xmldsig sibling, if imported, must sit next to it.

  Works in Windows PowerShell 5.1 and PowerShell 7+.

.PARAMETER Schema    path to FundsXML.xsd, or a remote URL
.PARAMETER XmlFile   the instance document to validate
.EXAMPLE
  pwsh XSD_Validation/cli/validate.ps1 `
    https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd `
    FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)] [string] $Schema,
  [Parameter(Mandatory = $true, Position = 1)] [string] $XmlFile
)
$ErrorActionPreference = 'Stop'

$origSchema = $Schema
$schemaPath = $Schema
$tmpDir = $null

$xmllint = Get-Command xmllint -ErrorAction SilentlyContinue
if ($xmllint -and $Schema -match '^https?://') {
  # Remote schema + xmllint: materialise it (and the xmldsig sibling it may
  # import) into a temp dir so the instance can be validated with --nonet.
  $tmpDir = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName()))
  $schemaPath = Join-Path $tmpDir 'FundsXML.xsd'
  Write-Host "schema: fetch $Schema" -ForegroundColor DarkGray
  Invoke-WebRequest -Uri $Schema -OutFile $schemaPath -MaximumRedirection 5 -UseBasicParsing
  if (Select-String -Path $schemaPath -Pattern 'xmldsig-core-schema\.xsd' -Quiet) {
    $sib = ($Schema -replace '/[^/]+$', '/xmldsig-core-schema.xsd')
    Write-Host "schema: fetch $sib" -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $sib -OutFile (Join-Path $tmpDir 'xmldsig-core-schema.xsd') -MaximumRedirection 5 -UseBasicParsing
  }
}

try {
  if ($xmllint) {
    & $xmllint.Source --noout --nonet --schema $schemaPath $XmlFile
    if ($LASTEXITCODE -eq 0) { Write-Host "VALID: $XmlFile (schema $origSchema)"; exit 0 }
    Write-Error "INVALID: $XmlFile (schema $origSchema)"; exit 1
  }

  # No xmllint: validate with the built-in .NET schema validator. The schema
  # set gets a URL resolver so a remote schema and the relative xmldsig import
  # resolve; the instance document is read with no resolver (XXE-hardened).
  Add-Type -AssemblyName System.Xml
  $set = New-Object System.Xml.Schema.XmlSchemaSet
  $set.XmlResolver = New-Object System.Xml.XmlUrlResolver
  [void]$set.Add($null, $schemaPath)
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
  if ($script:bad) { Write-Error "INVALID: $XmlFile (schema $origSchema)"; exit 1 }
  Write-Host "VALID: $XmlFile (schema $origSchema)"
  exit 0
}
finally {
  if ($tmpDir) { Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue }
}
