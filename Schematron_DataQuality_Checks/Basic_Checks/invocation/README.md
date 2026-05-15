# Schematron Invocation

Run `basic_checks.sch` against a FundsXML document from four stacks. Same
SVRL semantics and pass/fail definition everywhere.

## Why a Saxon-class processor is required

`basic_checks.sch` declares `queryBinding="xslt2"`. ISO Schematron is applied by
**compiling it to XSLT** (SchXslt does this) and running the result to produce an
**SVRL** report. That needs an XSLT 2.0 engine — Saxon. `xmllint`/`xsltproc`/
`lxml` (XSLT 1.0 only) **cannot** run this ruleset.

`tools/fetch-tools.sh` fetches the SchXslt CLI jar (a self-contained runner that
bundles its own Saxon) into `.lib/`.

## SVRL semantics & pass/fail

`svrl-summary.py` is the single source of truth, shared by every stack and CI:

| SVRL element | Meaning |
|--------------|---------|
| `svrl:failed-assert` `role="error"` | ERROR |
| `svrl:failed-assert` `role="warning"` | WARNING |
| `svrl:successful-report` | a `<report>` fired (WARNING/INFO) |

`--fail-on error` (default) exits 1 only on ERROR-role failures; `--fail-on any`
exits 1 on any failed-assert (including warnings).

> The canonical sample currently yields **0 errors + 12 warnings**. The
> warnings are advisory (4× the broad `ShareClass` rule also matching
> `AssetDetails/ShareClass`; 8× derivative assets without exposure info). The
> percentage-sum rule is now active — see
> [`../README.md`](../README.md#known-ruleset-fix).

## Stacks

| Stack | File | Runnable on this box |
|-------|------|----------------------|
| CLI | [`run-schematron.sh`](run-schematron.sh) | ✅ verified |
| Java (native) | [`SchematronValidate.java`](SchematronValidate.java) | ✅ verified (SchXslt Java API) |
| Python | [`validate_schematron.py`](validate_schematron.py) | needs `pip install saxonche` |
| .NET/C# | [`SchematronValidate.cs`](SchematronValidate.cs) | needs .NET SDK + `SaxonHE` package |
| shared | [`svrl-summary.py`](svrl-summary.py) | ✅ classifier used by all + CI |

Java classpath (the CLI jar already bundles Saxon — do **not** add the
standalone `Saxon-HE` jar, the two need different `org.xmlresolver` APIs):

```bash
tools/fetch-tools.sh
CP=.lib/schxslt-cli-1.10.1.jar:.lib/commons-cli-1.5.0.jar:.lib/slf4j-api-1.7.32.jar:.lib/slf4j-nop-1.7.32.jar
javac -cp "$CP" -d /tmp/scv Schematron_DataQuality_Checks/Basic_Checks/invocation/SchematronValidate.java
java  -cp "$CP:/tmp/scv" SchematronValidate Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch \
      FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml
```

## Quick check (positive + negative)

```bash
RS=Schematron_DataQuality_Checks/Basic_Checks/invocation/run-schematron.sh
$RS FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml          # exit 0 (0 errors)
$RS tests/fixtures/invalid/schematron-invalid_Positions.xml          # exit 1 (percentage 120%)
```
