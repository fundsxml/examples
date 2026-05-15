---
name: New example / enhancement
about: Propose a new sample, rule, language example or improvement
title: "[feat] "
labels: enhancement
---

**What & why**
The use case and who it helps (e.g. "import example in Go", "PRIIPS-KID
regulatory sample", "Schematron rule for X").

**Where it fits**
Which area: `FundsXML_Files/`, `XSD_Validation/`, `Schematron_…`,
`XSLT_…`, `XQuery_Examples/`, `XML_Signature/`, `Database_Integration/`,
`Large_File_Processing/`, `Data_Binding_JSON/`.

**Scope notes (per [CONTRIBUTING.md](../../CONTRIBUTING.md))**
- FundsXML version(s) involved; remember 4.0.0 has no `ControlData/Version`.
- Standalone & runnable (no DB server / Docker); English; teaching-grade comments.
- New samples must be XSD-valid against the official released schema; new
  round-trip examples must be proven with `xml_equiv.py` **+** XSD.

**Willing to contribute a PR?** yes / no
