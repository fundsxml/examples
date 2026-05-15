# XSLT Transformations

Company-facing transformations of FundsXML positions data. All stylesheets are
**XSLT 2.0** — run with Saxon (`xsltproc`/`lxml` are XSLT 1.0 and will not work).
`tools/fetch-tools.sh` provides Saxon-HE in `.lib/`.

| Output | Stylesheet | Notes |
|--------|-----------|-------|
| HTML factsheet | [`Factsheet/factsheet_html.xslt`](Factsheet/factsheet_html.xslt) | header, KPIs, share classes, top-10 holdings |
| PDF factsheet | [`Factsheet/factsheet_fo.xslt`](Factsheet/factsheet_fo.xslt) | emits XSL-FO → render with Apache FOP: `fop -fo out.fo -pdf out.pdf` |
| Positions CSV | [`CSV_Export/positions_csv.xslt`](CSV_Export/positions_csv.xslt) | RFC-4180 quoting; `delimiter` param |

Company-internal DQ rules live next door in
[`../XSLT_DataQuality_Checks/Custom_Internal_Checks/`](../XSLT_DataQuality_Checks/Custom_Internal_Checks/).

## Run (per stack)

| Stack | Entry point | Status |
|-------|-------------|--------|
| CLI (Saxon) | [`invocation/run-transform.sh`](invocation/run-transform.sh) | ✅ verified |
| Java (s9api, no JAXB) | [`invocation/RunTransform.java`](invocation/RunTransform.java) | ✅ verified |
| Python | [`invocation/run_transform.py`](invocation/run_transform.py) | needs `pip install saxonche` |
| Node.js | see below | needs `npm i xslt3` (saxon-js) |

```bash
# CLI — HTML factsheet
XSLT_Transformations/invocation/run-transform.sh \
  XSLT_Transformations/Factsheet/factsheet_html.xslt \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml factsheet.html

# CLI — CSV with semicolon delimiter (parameter pass-through)
XSLT_Transformations/invocation/run-transform.sh \
  XSLT_Transformations/CSV_Export/positions_csv.xslt \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml positions.csv "delimiter=;"

# PDF — two steps (Saxon then Apache FOP)
XSLT_Transformations/invocation/run-transform.sh \
  XSLT_Transformations/Factsheet/factsheet_fo.xslt \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml factsheet.fo
fop -fo factsheet.fo -pdf factsheet.pdf

# Node.js (SaxonJS / xslt3) — XSLT 3.0 engine runs these XSLT 2.0 sheets:
npx xslt3 -xsl:XSLT_Transformations/CSV_Export/positions_csv.xslt \
          -s:FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml -o:positions.csv
```

All transforms work unchanged on the 4.1.0 / 4.0.0 samples (backward
compatibility; no XML namespace in FundsXML 4.x).
