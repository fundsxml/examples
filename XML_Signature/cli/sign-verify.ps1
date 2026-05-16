<#
.SYNOPSIS
  Windows counterpart of sign-verify-xmlsec1.sh.

.DESCRIPTION
  xmlsec1 is a POSIX/native CLI with no first-class Windows build, so on
  Windows the command-line XML-signature path is the .NET example
  (XML_Signature/dotnet, System.Security.Cryptography.Xml) — same signature
  profile (RSA-SHA256, exclusive C14N, enveloped) as the verified Java
  example, so files cross-verify between stacks.

  This thin wrapper just forwards to that .NET project via `dotnet run`.
  Keys come from the cross-platform Java GenerateTestKey (no openssl):
    .\mvnw.cmd -q -pl XML_Signature/java compile exec:java -Dexec.mainClass=GenerateTestKey

.EXAMPLE
  pwsh XML_Signature/cli/sign-verify.ps1 sign FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml signed.xml
  pwsh XML_Signature/cli/sign-verify.ps1 verify signed.xml
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)] [string] $Mode,
  [Parameter(ValueFromRemainingArguments = $true)] [string[]] $Rest
)
$ErrorActionPreference = 'Stop'
$proj = Join-Path $PSScriptRoot '..\dotnet'

Write-Host "Windows CLI XML-signature -> .NET example ($proj)" -ForegroundColor DarkGray
& dotnet run --project $proj -- $Mode @Rest
exit $LASTEXITCODE
