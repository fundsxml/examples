# XQuery Examples

![XQuery](https://img.shields.io/badge/XQuery-3.1-blue) ![status](https://img.shields.io/badge/status-verified-brightgreen)

Read-only analytics over FundsXML with XQuery 3.1. Positions and assets are
joined by the shared `UniqueID` (the standard FundsXML link). FundsXML 4.x has
no XML namespace — queries use bare element names, so they work unchanged on the
4.2.9 / 4.1.0 / 4.0.0 samples.

| Query | Purpose | Notable |
|-------|---------|---------|
| [`aggregate-by-assettype.xq`](aggregate-by-assettype.xq) | Exposure grouped by `AssetType` | `group by`, grand-total reconciliation |
| [`top-holdings.xq`](top-holdings.xq) | N largest holdings, names resolved | external var `n` (default 10) |
| [`fund-summary.xq`](fund-summary.xq) | Fund/doc overview + reconciliation block | version-agnostic (4.0.0 has no `Version`) |
| [`look-through.xq`](look-through.xq) | Fund-of-funds look-through readiness | flags `SC` (fund) positions + weights |

## Run (per stack)

| Stack | Entry point | Status |
|-------|-------------|--------|
| CLI (Saxon) | [`invocation/run-xquery.sh`](invocation/run-xquery.sh) | ✅ verified |
| Java (s9api, no JAXB) | [`invocation/RunXQuery.java`](invocation/RunXQuery.java) | ✅ verified |
| Python | [`invocation/run_xquery.py`](invocation/run_xquery.py) | needs `pip install saxonche` |
| BaseX | see below | needs BaseX install |

```bash
tools/fetch-tools.sh
SRC=FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml

# CLI — to stdout
XQuery_Examples/invocation/run-xquery.sh XQuery_Examples/fund-summary.xq "$SRC"

# CLI — external variable + output file (Saxon Query: bare name=value)
XQuery_Examples/invocation/run-xquery.sh XQuery_Examples/top-holdings.xq "$SRC" top.xml n=5

# Java s9api
SCP=.lib/Saxon-HE-12.5.jar:.lib/xmlresolver-5.2.2.jar:.lib/xmlresolver-5.2.2-data.jar
javac -cp "$SCP" -d /tmp/xq XQuery_Examples/invocation/RunXQuery.java
java  -cp "$SCP:/tmp/xq" RunXQuery XQuery_Examples/aggregate-by-assettype.xq "$SRC"

# BaseX (in-memory, binds the document and the external variable)
basex -i "$SRC" -bn=5 XQuery_Examples/top-holdings.xq
```

Note: Saxon's `net.sf.saxon.Query` takes external variables as plain
`name=value` arguments — **not** `-param:` (that is the XSLT entry point) and
not `!name=value` (that sets serialization properties).
