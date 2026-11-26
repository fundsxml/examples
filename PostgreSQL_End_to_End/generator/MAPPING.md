# Mapping: database → FundsXML 4.2.9

The most important document of a generator: where every value of the file comes from. The business side
reviews this table, long before any file exists; change it together with `export.py`.

| FundsXML path | Source | Rule |
|---|---|---|
| `ControlData/UniqueDocumentID` | – | `EXAMPLE-AM-<partner>-<content date>`; an AMEND adds `-AMEND-1`. Never reused |
| `ControlData/DocumentGenerated` | – | now (fixed with `--generated` in tests) |
| `ControlData/ContentDate` | `--date` | the day the data is valid for |
| `ControlData/DataOperation`, `RelatedDocumentIDs` | `--amend` | `INITIAL`, or `AMEND` with the corrected document's ID |
| `Funds/Fund/Identifiers/LEI` | `fund.lei` | funds listed in `partners.json`; an umbrella brings its subfunds |
| `Fund/Names/OfficialName`, `ShortName`, `LanguageNames/Name[@language]` | `fund_name` | `kind`, `language` |
| `Fund/Currency` | `fund.currency` | |
| `Fund/SingleFundFlag` | `fund.single_fund_flag` | `false` → `Subfunds/Subfund` from `fund.parent_fund_id` |
| `Fund/FundStaticData` | `fund_static.details` | written back as delivered (block `static`) |
| `…DynamicData/TotalAssetValues/TotalAssetValue` | `nav` (`share_class_id IS NULL`) | one per date and `nature`; one `Amount` per `currency` |
| `TotalNetAssetValue/Amount/@isShareClassCcy`, `@isFundCcy` | `nav.is_share_class_ccy`, `is_fund_ccy` | only when true |
| `…/Portfolios/Portfolio/NavDate` | `portfolio.nav_date` | latest portfolio up to `--date` |
| `Portfolio/Positions/Position` | `position.details` | as delivered, `UniqueID` = `A` + `asset_id`; `TotalValue`, `TotalPercentage` from the columns |
| `Portfolio/Transactions/Transaction` | `trade.details` | `AssetUniqueID` = `A` + `asset_id`; container `from`/`to` = month of the portfolio |
| `Portfolio/Earnings/Earning` | `earning.details` | as for trades |
| `Portfolio/PositionsDecomposed` | `position` (`look_through`) | `LookThroughLevels` 1 |
| `ShareClass/Identifiers/ISIN`, `Names/OfficialName`, `Currency` | `share_class` | |
| `ShareClass/CurrencyHedgedFlag` | `share_class.hedged` | left out when unknown |
| `ShareClass/Prices/Price` | `price` | `ActionCode` = `C`; `NavDate`, `PriceCurrency`, `PriceNature`, `NavPrice`, `SubscriptionPrice`, `RedemptionPrice` |
| `ShareClass/TotalAssetValues/TotalAssetValue` | `nav` (`share_class_id`) | as for the fund, plus `SharesOutstanding` |
| `ShareClass/Distributions/Distribution` | `distribution` | `DividendStatus`, dates, gross and net per share |
| `ShareClass/Flows/Flow` | `sc_flow` | month of the portfolio; `TransactionType` `SUB`/`RED` |
| `AssetMasterData/Asset` | `asset`, `asset_identifier` | only assets the file refers to; no ISIN → `OtherID[@FreeType='SUPPLIER']` = our key |
| `Asset/AssetDetails` | `asset.details` | as delivered |
| `Documents/Document` | `document`, `document_target` | documents in force on `--date` for the partner's funds and share classes; `DocumentURL` or `BinaryData` (base64, 76 characters per line) |
| `RegulatoryReportings/DirectReporting/EMT_V4_2/FinancialInstrument` | `regulatory_report.content` | template `EMT`, share classes of the file |
| `RegulatoryReportings/DirectReporting/EET1.1.3/EET1.1.3` | `regulatory_report.content` | template `EET` |
| `RegulatoryReportings/IndirectReporting/TripartiteTemplateSolvencyII_V7/Portfolio` | `regulatory_report.content` | template `TPT` |

Formats everywhere: decimal point, no thousands separators, ISO dates, `true`/`false`, UTF-8. What is
missing in the database is left out of the file: no empty elements, no placeholders.
