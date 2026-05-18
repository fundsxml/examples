<!-- Thanks for contributing! Please read CONTRIBUTING.md first. -->

## What & why

<!-- One or two sentences: what this changes and the use case it serves. -->

## Area

<!-- e.g. Database_Integration/python, XSLT_Transformations, a new sample, … -->

## Checklist (see [CONTRIBUTING.md](../CONTRIBUTING.md))

- [ ] Branched off the **latest `main`** (not stacked on another open PR).
- [ ] One focused change; relevant **README(s) updated** in this PR.
- [ ] English only; example is **self-contained** and **heavily commented**
      (file-header: purpose / run / deps / FundsXML assumptions + what & why).
- [ ] FundsXML conventions: no XML namespace; XSD-validated against the
      **official released schema** (validators take `<schema> <xml-file>` —
      release URL or local path); 4.0.0 has no `ControlData/Version`;
      secure XML parsing (DTD/external entities off).
- [ ] New/changed samples are **XSD-valid**; negative fixtures still fail.
- [ ] Round-trip examples: proven with `Database_Integration/tools/xml_equiv.py`
      **and** `xmllint --schema` (complementary checks).
- [ ] Schematron/XSLT tolerance or pattern changes mirrored on both sides +
      both READMEs.
- [ ] **CI is green** (`.github/workflows/ci.yml` — validates everything).

## Verification

<!-- The exact commands you ran and their result. No "should pass". -->
