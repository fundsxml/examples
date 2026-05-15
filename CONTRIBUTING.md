# Contributing

Thanks for improving the FundsXML enterprise examples. This repo is a
**reference**: every example must be runnable, self-explanatory, and verified.
Please read this before opening a pull request.

## Ground rules

- **English only.** All code/XML comments, READMEs and docs are in English.
- **Examples are teaching artifacts.** Comment generously: a file-header block
  (purpose, exact run command, dependencies, FundsXML assumptions) plus
  *what & why* comments on non-obvious logic. A developer should be able to
  reimplement the pattern from the comments alone.
- **One README per component**, kept in sync with the code it documents.
- **No new runtime services.** No databases servers, no Docker — examples must
  run standalone (SQLite, fetched jars, pure-language libs).

## FundsXML conventions

- **FundsXML 4.x has no XML namespace** — use bare element names in XPath;
  never introduce a default namespace or prefixes (except `ds:`/`xsi:` where
  the schema itself requires them). `xsi:noNamespaceSchemaLocation` must be in
  the XMLSchema-instance namespace or validators reject it.
- **Validate against the official released schema**, never a hand-made
  catalog: fetch with `tools/fetch-schema.sh <version>` (it handles GitHub's
  302 redirect and the relative `xmldsig-core-schema.xsd` import that 4.2.9+
  needs). Set sample `xsi:noNamespaceSchemaLocation` to that release URL.
- **4.0.0 `ControlData` has no `<Version>` element** (added in 4.1.0) — never
  add one to a 4.0.0 sample.
- Positions ↔ Assets link by a shared `UniqueID`; `AssetMasterData` is
  document-scoped. Keep Schematron and Basic-XSLT **tolerances identical**
  (NAV sum < 1 ccy unit, percentage sum ≤ 1%, price calc < 0.1) and update
  both READMEs together when changing one.
- **ISO Schematron matches only the first rule per pattern**: keep at most one
  rule per node-context per `<pattern>` (put others in their own pattern), or
  later rules become dead code.
- **Secure XML parsing everywhere**: disable DTDs / external entities
  (`resolve_entities=False` + `no_network=True`, `disallow-doctype-decl`,
  `XmlResolver=null`, `--nonet`, `FEATURE_SECURE_PROCESSING`).

## Samples & round-trips

- New samples must be **XSD-valid** against their version's official schema and
  carry a per-example README with a version badge and the validated-against URL.
- Keep the committed positive samples passing; deliberately broken inputs go in
  `tests/fixtures/invalid/` and must fail their check (CI asserts this).
- For import/export (round-trip) examples: prove **import file == export file**
  with `Database_Integration/tools/xml_equiv.py` (it ignores the volatile
  `DocumentGenerated` timestamp and numeric/whitespace/attr-order; child order
  is significant) **and** XSD-validate the output — `xml_equiv` ignores
  `xmlns`, so the two checks are complementary. Author round-trip fixtures
  *lossless* (only model-captured elements) so equality is achievable.

## Local verification (before you push)

Run what you changed and confirm it actually works — no "should pass" claims.

```bash
tools/fetch-schema.sh 4.2.9            # XSD cache (gitignored)
tools/fetch-tools.sh                   # Saxon / SchXslt / sqlite-jdbc / Santuario

xmllint --noout --schema .schema-cache/4.2.9/FundsXML.xsd <your-sample>.xml
Schematron_DataQuality_Checks/Basic_Checks/invocation/run-schematron.sh <sample>.xml
# DB round-trip example:
python3 Database_Integration/python/import_fundsxml.py fx.db <sample>.xml
python3 Database_Integration/python/export_fundsxml.py fx.db <docId> out.xml
python3 Database_Integration/tools/xml_equiv.py <sample>.xml out.xml
```

Toolchain notes: the SchXslt CLI jar bundles its own Saxon — do **not** add the
standalone `Saxon-HE` jar to its classpath. The working tree may sit on a
WebDAV mount that creates `.DS_Store`/`._*` — these are gitignored; never
`git add` them.

## Pull requests

- Branch off the **latest `main`** (`git fetch origin && git switch -c <name> origin/main`).
  **Do not stack a PR on another unmerged branch** — the repo auto-deletes
  head branches on merge, which would orphan your base.
- One focused change per PR; update the relevant README(s) in the same PR.
- CI (`.github/workflows/ci.yml`, job `validate`) must be green — it
  fetches schemas, validates every sample (XSD + Schematron), runs the
  transform/XQuery/signature/DB/large-file/JSON smoke tests, and asserts the
  negative fixtures fail. Confirm green before marking a PR ready.
- A maintainer merges PRs. End commit messages and PR descriptions per the
  repo's existing style.

## Licensing

By contributing you agree your work is licensed under the repository's
[Apache License 2.0](LICENSE).
