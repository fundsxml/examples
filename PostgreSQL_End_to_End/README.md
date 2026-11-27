# FundsXML end to end with PostgreSQL

![FundsXML 4.2.9](https://img.shields.io/badge/FundsXML-4.2.9-blue) ![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791) ![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen)

A complete example for the films of the series **"FundsXML in production"**
(<https://fundsxml.github.io/videos/>): *FundsXML in a database*, *Loading FundsXML files* and
*Generating FundsXML*. Everything the films show is in this folder: the table model, the loader, the
generator, the sample deliveries and the files the generator writes.

**This is an example, not a product.** The code is short on purpose (about 1,500 lines of SQL and
Python), and the comments explain *why* rather than *what*. Take the ideas, not the code.

**Download:** [`PostgreSQL_End_to_End.zip`](https://github.com/fundsxml/examples/releases/download/postgres-end-to-end-v1/PostgreSQL_End_to_End.zip)
(this folder only), or the whole repository with *Code → Download ZIP*.

```mermaid
flowchart LR
    A[data/in<br/>FundsXML deliveries] --> B[landing folder]
    B --> C[loader/load.py<br/>check · validate · register<br/>stream · link · codes · reconcile]
    C --> D[(PostgreSQL<br/>ddl/*.sql)]
    D --> E[generator/export.py<br/>partner register]
    E --> F[XSD 1.1 validation]
    F --> G[data/expected<br/>one file per partner]
```

## What is in it

| Path | What it shows |
|---|---|
| [`ddl/`](ddl/) | The table model in eight files: deliveries and findings, master data, time series, transactions, documents, regulatory templates, views for users, access with row-level security; plus the code lists from the schema |
| [`loader/load.py`](loader/load.py) | `check → validate → register → stream → link → codes → reconcile → status`, one transaction per file, a report for every rejected file |
| [`generator/export.py`](generator/export.py) | One file per partner from the [partner register](generator/partners.json), streamed in strict schema order; `--amend` writes a correction. The [mapping table](generator/MAPPING.md) says where every value comes from |
| [`data/in/`](data/in/) | Six deliveries of a fictional asset manager (below) |
| [`data/bad/`](data/bad/) | Four files a loader must not accept |
| [`data/expected/`](data/expected/) | The files the generator writes from the loaded data (golden files) |
| [`queries/`](queries/) | The questions of the films: deliveries, what repeats, NAV as known today and before, positions, transactions, documents, templates, access, reconciliation, rows per table |
| [`run_all.sh`](run_all.sh) | The whole chain end to end; CI runs exactly this |
| [`tools/xsd11/`](tools/xsd11/) | XSD 1.1 validation with Xerces-J 2.12.2 (jars from Maven Central, checked by SHA-1) |

## The deliveries

All companies, funds and identifiers are fictitious (ISINs and LEIs with `XMPL`); the funds are those of
[`FundsXML_Files/4.2.9/realistic`](../FundsXML_Files/4.2.9/realistic/), arranged by
[`data/make_samples.py`](data/make_samples.py) so that every repeating node of FundsXML really repeats.

| File | Content |
|---|---|
| `01_month-end_2025-10-31.xml` | **Four funds in one file**: an umbrella (*Example Invest SICAV*) with two subfunds, and two single funds. 11 share classes in EUR, USD and CHF with a daily NAV history (264 prices), 522 positions (incl. a look-through of the fund of funds), 209 trades, 68 income records, 67 subscriptions and redemptions, 3 distributions, 430 assets shared by all funds; EMT V4.2, EET 1.1.3 and TPT V7 |
| `02_nav_2025-11-05.xml` | Daily NAVs of 2025-11-03 to 2025-11-05 for every fund and share class: **an ESTIMATED and an OFFICIAL NAV per day**, net assets in share-class and fund currency |
| `03_documents_2025-11-03.xml` | Prospectus as a link, PRIIPs KIDs in **English and German** as links, a KID and a factsheet **embedded** as PDF |
| `04_nav_2025-11-05_amend.xml` | **AMEND** of 02: the official NAV of the CHF class on 2025-11-04 corrected |
| `05_nav_2025-11-06_sent-by-mistake.xml` | A delivery sent by mistake ... |
| `06_nav_2025-11-06_delete.xml` | ... and its **DELETE** |
| `bad/cut-off.xml` | Cut off during transfer → rejected (`INCOMPLETE`) |
| `bad/wrong-order.xml` | `Currency` before `Names` → rejected (`SCHEMA`) |
| `bad/unknown-sender.xml` | A data supplier not in `loader/senders.json` → rejected (`UNKNOWN_SENDER`) |
| `bad/duplicate-of-02.xml` | Same document ID as 02 → skipped, never loaded twice |

## The table model

Every repeating node of FundsXML is a row, never a column:

| FundsXML | Table | Repeats per |
|---|---|---|
| `ControlData` | `delivery` | file; `unique_document_id` makes loading idempotent, `raw` keeps the file |
| `Funds/Fund`, `Subfunds/Subfund` | `fund` | file; `parent_fund_id` = umbrella |
| `Names`, `Identifiers` | `fund_name`, `fund_identifier` | fund, language, scheme |
| `FundStaticData` | `fund_static` | fund and delivery (XML plus a few columns) |
| `ShareClasses/ShareClass` | `share_class` | fund or subfund |
| `Prices/Price` | `price` | share class, date, nature |
| `TotalAssetValues/TotalAssetValue` | `nav` | fund or share class, date, nature, **currency** |
| `Portfolios/Portfolio` | `portfolio` | fund and date |
| `Positions/Position`, `PositionsDecomposed` | `position` | portfolio (`look_through` true/false) |
| `AssetMasterData/Asset` | `asset`, `asset_identifier` | our own key; all identifiers in their own table |
| `Flows/Flow`, `Distributions/Distribution` | `sc_flow`, `distribution` | share class |
| `Transactions/Transaction`, `Earnings/Earning` | `trade`, `earning` | portfolio |
| `Documents/Document` | `document`, `document_target` | document; linked (`url`) or embedded (`content`) |
| `RegulatoryReportings` | `regulatory_report` | template record: XML plus key fields |

Design decisions:

- **Idempotent.** A document ID seen before is skipped; loading the same folder twice is harmless.
- **Versioned.** Time-series rows carry the delivery that brought them and the one that replaced them
  (`replaced_by_delivery_id`). The latest delivery for the same key wins; an `AMEND` or `DELETE` takes back
  everything its related document delivered. History stays queryable (`queries/03_nav_history.sql`).
- **Our own keys.** A FundsXML `UniqueID` is only valid inside one file. Assets are found by ISIN (or WKN,
  SEDOL, CUSIP); an asset without any identifier gets the key *data supplier / asset type / file ID*, which
  the generator passes on as `<OtherID FreeType="SUPPLIER">`, so the round trip finds every asset again.
- **Amounts with their currency.** One row per currency, with the fund- and share-class-currency flags.
- **XML where it pays.** `AssetDetails`, positions, trades, static data and regulatory templates keep their
  XML next to the columns that queries need: dozens of instrument types and template versions, without a
  table for each.
- **Flat memory.** The loader streams with `lxml.etree.iterparse` and drops every element after use;
  positions wait in `position_staging` because `AssetMasterData` comes after the funds in the file. The
  generator streams with `lxml.etree.xmlfile` and a server-side cursor.
- **Quality with the data.** Unknown codes and failed reconciliations are stored in `delivery_finding`; a
  delivery with errors stays `loaded` (held back), a clean one becomes `checked` and can be released
  (`release_delivery()`), with name and time. The views show released data only.
- **Access.** Roles for reading and releasing; readers see only their client's portfolios (row-level
  security, `ddl/08_access.sql`, `queries/08_access.sql`).
- **XSD 1.1.** The FundsXML 4.2.x schema declares XSD 1.1; `xmllint` and lxml only implement XSD 1.0, so
  validation runs [Xerces-J 2.12.2 (XSD 1.1 build)](tools/xsd11/validate.sh).

## Quick start

Requirements: Docker, Python 3.11+, Java 17+ (for the validation), `psql`.

```bash
cd PostgreSQL_End_to_End
docker compose up -d --wait                       # PostgreSQL 16 with ddl/*.sql; POSTGRES_PORT=5433 to change the port
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

mkdir -p schemas/4.2.9
curl -sSLfo schemas/4.2.9/FundsXML.xsd https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
curl -sSLfo schemas/4.2.9/xmldsig-core-schema.xsd https://github.com/fundsxml/schema/releases/download/4.2.9/xmldsig-core-schema.xsd
export FUNDSXML_XSD=$PWD/schemas/4.2.9/FundsXML.xsd
export DATABASE_URL=postgresql://fundsxml:fundsxml@localhost:5432/fundsxml
export PGHOST=localhost PGUSER=fundsxml PGPASSWORD=fundsxml PGDATABASE=fundsxml

./run_all.sh                                      # everything below in one go (recreates the tables)

# or step by step
python loader/load.py --release-by "data team" data/in       # load
python loader/load.py data/in                                 # again: every file is skipped
python loader/load.py data/bad                                # rejected, with the reason
psql -f queries/03_nav_history.sql                            # NAV as known today and before the AMEND
python generator/export.py --all --date 2025-11-05 --out out/ # one file per partner
tools/xsd11/validate.sh "$FUNDSXML_XSD" out/*.xml
```

Output of the loader for the month-end file:

```text
file       01_month-end_2025-10-31.xml
check      EXAMPLE-AM-MONTHEND-2025-10-31, INITIAL, content date 2025-10-31, from EXAMPLE-AM
validate   ok: valid against FundsXML.xsd (XSD 1.1)
register   delivery 1
stream     5 funds, 11 share classes, 264 prices, 19 navs, 522 positions, 209 trades, 68 income, 67 flows, 3 distributions, 430 assets, 430 new assets, 12 templates
link       522 positions linked to assets
codes      12 distinct codes checked against code_list
reconcile  Example Global Equity Fund 2025-10-31: positions 602060878.93 vs net assets 602060878.93 EUR, weights 100.0000 % -> ok
...
status     released
```

## Limits

Deliberately left out, to keep the example short: subfund static data, breakdowns, risk codes, fees,
performance figures, benchmarks and country-specific data are kept in the original file (`delivery.raw`)
but not in tables; the generator writes FundsXML 4.2.9 only; the landing folder is a plain directory.
