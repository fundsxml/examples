# Custom Internal DQ Checks

![XSLT](https://img.shields.io/badge/XSLT-2.0-blue) ![status](https://img.shields.io/badge/status-verified-brightgreen)

Example **company-internal** house rules layered on top of XSD + Schematron
validation — the kind of checks an asset manager adds beyond the FundsXML
standard. XSLT 2.0, self-contained HTML report.

| Rule | Description | Default |
|------|-------------|---------|
| R1 | AssetType whitelist — only approved asset types held | `EQ BO SC OP FU FX SW WA CE AC RP RE CM` (param `allowedAssetTypes`) |
| R2 | Position `UniqueID` convention — `ID_<≥3 digits>` | — |
| R3 | Concentration limit — no single position over the cap | 20% (param `concentrationLimitPct`) |
| R4 | OTC derivative (FX, SW) must carry a counterparty LEI | — |

On the canonical 4.2.9 sample all four rules **PASS** (verified).

## Run

Run the generic XSLT runner via the committed Maven Wrapper (`mvnw.cmd` on
Windows), from the repo root:

```bash
M="./mvnw -q -pl XSLT_Transformations/invocation compile exec:java"
XSL=XSLT_DataQuality_Checks/Custom_Internal_Checks/custom_internal_checks.xslt
SRC=FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml

$M -Dexec.args="$XSL $SRC custom_dq.html"

# Tighten the concentration limit to 5% to see R3 fail:
$M -Dexec.args="$XSL $SRC custom_dq.html concentrationLimitPct=5"
```

XSLT 2.0 → use Saxon (see [`../../XSLT_Transformations/`](../../XSLT_Transformations/)
for per-stack invocation). `xsltproc`/`lxml` (XSLT 1.0) cannot run it.
