<!--
  Example README template — copy into each example directory and fill in.
  Keep it scannable. All content in English.
-->
# <Component> — <Short Title>

![Version](https://img.shields.io/badge/FundsXML-<X.Y.Z>-blue) ![status](https://img.shields.io/badge/status-runnable-brightgreen)

| Property | Value |
|----------|-------|
| **What** | One sentence: what this example demonstrates |
| **FundsXML version(s)** | e.g. 4.2.9 (works on 4.1.0/4.0.0 too — note differences) |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/<X.Y.Z>/FundsXML.xsd` |
| **Stacks** | CLI / Python / Java / .NET / PowerShell (list what is provided) |

## Purpose

Why this exists and when an enterprise integrator would use it.

## Prerequisites

- Tooling/runtime versions
- The example resolves the XSD itself (env `FUNDSXML_SCHEMA_DIR` →
  `.schema-cache/` → official-release download); or
  `python -m fundsxml_schema <version>` to pre-cache for a bare xmllint
- Network/proxy note when the official schema URL must be reached
  (`$FUNDSXML_SCHEMA_DIR` is the offline escape hatch)

## Run

Provide a runnable command per applicable stack:

```bash
# CLI
...
```
```bash
# Python
...
```
<!-- Java / .NET / PowerShell as applicable -->

## Expected output

What a correct run produces (and what failure looks like).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| ... | ... | ... |
