---
name: Bug report
about: An example doesn't run, or validation/round-trip is wrong
title: "[bug] "
labels: bug
---

**Which example / component**
e.g. `Database_Integration/python/export_fundsxml.py`, `XSD_Validation/java`,
`XSLT_Transformations/Factsheet`, the Schematron ruleset, …

**FundsXML version & sample**
e.g. 4.2.9, `FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml`
(or attach/inline a minimal FundsXML snippet — no real/PII data).

**What I ran**
The exact command(s), including the `./mvnw` (or `mvnw.cmd`) invocation for
Java examples, or any `tools/fetch-schema.sh` step.

**Expected vs. actual**
What you expected and what happened (paste the full error / output).

**Environment**
OS; and the relevant runtime version: Python / Java (`java -version`) /
Node (`node -v`) / .NET (`dotnet --version`) / `xmllint --version`.

**Validation already done** (helps a lot)
- [ ] `xmllint --noout --schema .schema-cache/<ver>/FundsXML.xsd <file>` result: …
- [ ] round-trip checked with `Database_Integration/tools/xml_equiv.py` (if applicable): …
