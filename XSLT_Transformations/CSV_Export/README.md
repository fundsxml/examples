# CSV Export (XSLT 2.0)

Two text-output XSLT 2.0 stylesheets that flatten FundsXML 4.x position data
into CSV. Both use bare-element XPath (FundsXML 4.x has **no XML namespace**)
and RFC-4180 quoting, and both take an optional `delimiter` parameter
(default `,`).

| Stylesheet | Output | Purpose |
|---|---|---|
| `positions_csv.xslt` | 19 columns, one row per position | Compact "flatten positions joined to asset master data" example: fund/document context, instrument identification, the holding's quantity & price, position value in both quotation and fund currency, and (for bonds) maturity / coupon / issuer. |
| `tpt_v7_export.xslt` | **152 columns**, one row per position | Reproduces the **TPT V7.0** (Tripartite Template) Solvency-II look-through reporting layout. |

## What the TPT export is

The **Tripartite Template (TPT)** is the FinDatEx / EFAMA industry standard that
fund managers use to deliver "look-through" holdings to insurers for Solvency II.
Per fund/share-class it lists every instrument the fund holds, described by a
fixed set of **152 data columns** (`1_…` … `1000_TPT_Version`).

The authoritative column list — and the FundsXML mapping for almost every field
— is taken from the FinDatEx **TPT V7.0** template spreadsheet (sheet
*"TPT V7.0"*, column *"Fundxml data name and path"*), published at
<https://findatex.eu/>. The spreadsheet is not part of this repository.

`tpt_v7_export.xslt` emits the TPT column names verbatim as the header row, then
**one full position block per share class (ISIN)** of every `<Fund>` — a single
TPT CSV may carry several ISINs. A fund with *N* share classes and *M* positions
produces *N×M* data rows; the share-class identification (cols 1, 2, 3, 8, 8b)
varies per ISIN while the NAV (col 5) and look-through positions stay at fund
level so the valuation weights reconcile. Funds without a share class emit one
block keyed by the fund ISIN/LEI.

## Running

Use the project's Saxon runner (XSLT 2.0; `xsltproc` is XSLT 1.0 only and will
not work). Java (`./mvnw`) and Python (`saxonche`, from the repo `.venv`) both
work — run from the repo root:

```bash
# Python / saxonche
.venv/bin/python XSLT_Transformations/invocation/run_transform.py \
    XSLT_Transformations/CSV_Export/tpt_v7_export.xslt \
    FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml  out_tpt.csv

# Java / Saxon-HE via the Maven wrapper
./mvnw -q -pl XSLT_Transformations/invocation compile exec:java \
    -Dexec.args="XSLT_Transformations/CSV_Export/tpt_v7_export.xslt \
                 FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml out_tpt.csv"

# Different delimiter, e.g. semicolon:
#   ... run_transform.py <xslt> <xml> <out> "delimiter=;"
```

The stylesheet has been exercised against the canonical
`FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml` (12 asset types,
21 positions × 2 share classes = 42 rows) and the multi-fund
`Multi-Fund_Positions.xml`. Every output row has exactly 152 columns and
parses cleanly as RFC-4180 CSV; the header is joined with the same
`delimiter` as the data rows.

## How FundsXML maps onto TPT

TPT's column-2 paths are *conceptual*. In real FundsXML 4.x the data for one TPT
line is split across two places, joined by the position's `<UniqueID>`:

- **Holding / valuation** — `Funds/Fund/FundDynamicData/Portfolios/Portfolio/Positions/Position`
- **Static / issuer master data** — `AssetMasterData/Asset[UniqueID = …]`

A `<Position>` carries exactly **one "holding" child** whose element name is the
instrument family (`Bond`, `Equity`, `ShareClass`, `Warrant`, `Option`,
`Future`, `FXForward`, `Swap`, `Repo`, `RealEstate`, `CallMoney`, `Account`,
`FixedTimeDeposit`, …). The stylesheet selects it generically (`$hold`), so
quantity / price / market value / accrued interest read uniformly across types.

### Mapped fields

| TPT column(s) | FundsXML source | Notes |
|---|---|---|
| `1` Portfolio id | `ShareClass/Identifiers/ISIN` → `Fund/Identifiers/ISIN` → `Fund/Identifiers/LEI` | per share class (one block each) |
| `2` Id code type | derived | `1` if an ISIN was used, else `99` (undertaking code) |
| `3` Portfolio name | `ShareClass/Names/OfficialName` → `Fund/Names/OfficialName` | |
| `4` Portfolio currency | `Fund/Currency` | This is the portfolio currency **(B)** |
| `5` Net asset value | `Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=fund-ccy]` | |
| `6` Valuation date | `Portfolio/NavDate` (→ `TotalAssetValue/NavDate`) | |
| `7` Reporting date | `ControlData/ContentDate` | |
| `8` Share price | `ShareClass/Prices/Price/NavPrice` | per share class (one block each) |
| `8b` Number of shares | `ShareClass/TotalAssetValues/TotalAssetValue/SharesOutstanding` | |
| `9` Cash ratio | **derived** = Σ `TotalPercentage` of all `AssetType` `AC`/`CM`/`FT` positions ÷ 100 | fund-level; `1 = 100%` |
| `12` CIC code | **derived** = 2-char country + 1-char category | see *CIC heuristic* below |
| `14` Instrument id | `Position/Identifiers/ISIN` → `Asset/Identifiers/ISIN` → **`Asset/UniqueID`** | always populated |
| `15` Instrument id type | derived | `1` (ISIN), else `99` (undertaking code, for the UniqueID fallback) |
| `17` Instrument name | `Asset/Name` | |
| `18` Quantity | `$hold/(Units\|Shares\|Contracts)` | unit-quoted instruments only |
| `19` Nominal amount | `$hold/Nominal` (→ market value for cash/deposits/derivatives) | exactly one of `18`/`19` is filled per row |
| `21` Quotation currency | `Position/Currency` | quotation currency **(A)** |
| `22` Market value QC | `$hold/MarketValue/Amount[@ccy=quote-ccy]` | |
| `23` Clean value QC | `22 − $hold/InterestClaimGross/Amount` | dirty minus accrued (bonds) |
| `24` Market value PC | `Position/TotalValue/Amount[@ccy=fund-ccy]` | |
| `25` Clean value PC | `24 − accrued (PC)` | |
| `26` Valuation weight | `Position/TotalPercentage ÷ 100` | percent → fraction of NAV |
| `27`/`28` Market exposure QC/PC | `Position/Exposures/Exposure/Value/Amount[@ccy …]` | commitment approach |
| `30` Exposure weight | `28 ÷ NAV` (→ falls back to `26`) | |
| `33` Coupon rate | `Asset/AssetDetails/Bond/Coupon/InterestRate` (→ legacy `Bond/InterestRate`) | |
| `38` Coupon frequency | `Asset/AssetDetails/Bond/Coupon/PaymentFrequency` | |
| `39` Maturity date | `Asset/AssetDetails/Bond/MaturityDate` | |
| `46` Issuer name | `Asset/AssetDetails/*/Issuer/Name` | any family child (`Bond`/`Equity`/`ShareClass`/…) |
| `47` Issuer id code | `…/Issuer/Identifiers/LEI` | |
| `48` Issuer id type | derived | closed list `1` = LEI, `9` = None |
| `52` Issuer country | `…/Issuer/Address/Country` → `Asset/Country` | |
| `117` Fund issuer name | `ControlData/DataSupplier/Name` | data supplier proxy |
| `122` Fund issuer country | `ControlData/DataSupplier/SystemCountry` | |
| `131` Underlying asset category | derived from `Asset/AssetType` | SII S.06.03 closed list (`2`,`3L`,`4`,`7`,`A`,`D`,…) |
| `1000` TPT version | constant `V7.0` | |

### Empty (structurally present) fields

The remaining TPT columns are emitted **empty** but kept in the layout so the
output stays structurally faithful to the template. These cover, among others:
derivative characteristics (`60`–`65`), the derivatives **underlying asset**
block (`67`–`89`), risk analytics (`90`–`94b`, `124`), look-through control
(`95`), indicative **SCR contributions** (`97`–`105b`), QRT instrument extras
(`106`–`114`), most QRT portfolio characteristics (`115`, `116`, `118`–`123a`,
`125`, `126`), convertible-bond specifics (`127`, `128`), no-yield-curve
specifics (`129`, `130`), and the V4–V7 add-on fields (`132`–`148`).

**Why empty?** `FundsXML.xsd` *does* define matching nodes for most of these
(e.g. `ModifiedDuration`, `CreditQualityStep`, `Coupon/PaymentFrequency`,
`Subordinated`, `Securitisation`, issuer-group elements) — they are simply
**not populated** in the sample files. Point this stylesheet at a FundsXML file
that carries those elements and the corresponding columns will fill in; extend
the mapped block in `tpt_v7_export.xslt` the same way the bond/issuer fields are
wired today.

### CIC heuristic (column 12)

FundsXML has no single CIC element, so the CIC code is **derived**:

- **Country** (chars 1–2) = `Asset/Country`, falling back to the first two
  characters of the ISIN (which carry the ISO country code). When neither is
  available (typical for OTC derivatives with no ISIN), the CIC is left empty.
- **Category** (char 3) is mapped from `Asset/AssetType`:
  `BO→2`, `EQ`/`WA→3`, `SC→4`, `CE→5`, `AC`/`CM`/`FT`/`RP→7`, `RE→9`, `FU→A`,
  `OP→B`, `SW→D`, `FX→E`, otherwise `0` (Other).

This is best-effort: FundsXML cannot distinguish government vs corporate bonds
(both `2` here) or call vs put options (both `B`), and only the country +
category portion of the full 4-character CIC is produced.
