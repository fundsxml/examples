# Large-File / Streaming Processing

![status](https://img.shields.io/badge/Python%20%2B%20Java%20StAX-verified-brightgreen)

Enterprise FundsXML feeds can be hundreds of MB. Loading them into a DOM blows
memory; these examples process them **streaming, at constant memory** —
verified: ~16 MiB RSS (Python) / ~2 MiB heap (Java, `-Xmx64m`) for a 20 000-
position file, independent of file size.

| Tool | What | Status |
|------|------|--------|
| [`python/make_large_sample.py`](python/make_large_sample.py) | Generate a big XSD-valid file by streaming **writes** | ✅ |
| [`python/stream_aggregate.py`](python/stream_aggregate.py) | `lxml.iterparse` aggregation (clears parsed siblings) | ✅ |
| [`java/StreamAggregate.java`](java/StreamAggregate.java) | StAX pull parser, native Java (no JAXB/DOM) | ✅ |
| [`python/split.py`](python/split.py) | Split into independently **XSD-valid** chunks | ✅ |
| [`python/delta_diff.py`](python/delta_diff.py) | INITIAL-vs-DELTA position diff (added/removed/changed) | ✅ |

FundsXML 4.x has no XML namespace — matchers use the bare `Position` tag.
Parsers disable DTD/external entities (XXE-safe).

## Run

```bash
# 1. synthetic 50k-position file (~constant-memory writer)
python3 Large_File_Processing/python/make_large_sample.py big.xml 50000

# 2. aggregate — Python and Java give identical totals at flat memory
python3 Large_File_Processing/python/stream_aggregate.py big.xml
# Java via the committed Maven Wrapper (mvnw.cmd on Windows); a small heap
# proves the constant-memory claim.
MAVEN_OPTS=-Xmx64m ./mvnw -q -pl Large_File_Processing/java compile exec:java \
  -Dexec.args="big.xml"

# 3. split into XSD-valid chunks of 10k positions
python3 Large_File_Processing/python/split.py big.xml chunks/ 10000
XSD_Validation/cli/validate.sh \
  https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd \
  chunks/chunk-0001.xml   # or a local FundsXML.xsd path

# 4. day-over-day position delta (exit 1 if anything changed)
python3 Large_File_Processing/python/delta_diff.py yesterday.xml today.xml
```

## ETL note

The streaming readers are the natural building block for ETL pipelines
(Apache Camel / NiFi / Spring Batch): a `split` step feeds a parallel
`stream_aggregate`/load stage, and `delta_diff` drives incremental upserts when
a feed alternates `DataOperation` INITIAL/DELTA. Example Camel route shape:

```
from("file:in?include=.*\\.xml")
  .to("exec:python3?args=Large_File_Processing/python/split.py ${file} work/")
  .split(...).parallelProcessing()
  .to("exec:...stream_aggregate.py ...")   // or a JDBC load (see Database_Integration/)
```

CI runs steps 2–4 on a generated file (totals asserted, a chunk XSD-validated).
