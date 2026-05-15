-- FundsXML -> PostgreSQL (code reference; no DB is provisioned in this repo).
--
-- Strategy: stage the document in a native `xml` column, then shred with
-- XMLTABLE. FundsXML 4.x has no namespace, so XPath uses bare element names.
-- Schema: ../ddl/schema.sql (run that first, plus the staging table below).

CREATE TABLE IF NOT EXISTS fundsxml_stage (
    document_id text PRIMARY KEY,
    doc         xml NOT NULL
);

-- Load the file into the stage (psql):
--   \set content `cat FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml`
--   INSERT INTO fundsxml_stage
--     SELECT (xpath('/FundsXML4/ControlData/UniqueDocumentID/text()',
--                   x.doc))[1]::text, x.doc
--     FROM (SELECT :'content'::xml AS doc) x;

-- fund -----------------------------------------------------------------------
INSERT INTO fund (document_id, lei, official_name, currency,
                  content_date, nav_date, total_nav, fxml_version)
SELECT s.document_id, f.lei, f.official_name, f.currency,
       f.content_date, f.nav_date, f.total_nav, f.fxml_version
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4' PASSING s.doc COLUMNS
        lei           text          PATH 'Funds/Fund/Identifiers/LEI',
        official_name text          PATH 'Funds/Fund/Names/OfficialName',
        currency      text          PATH 'Funds/Fund/Currency',
        content_date  date          PATH 'ControlData/ContentDate',
        fxml_version  text          PATH 'ControlData/Version',
        nav_date      date          PATH 'Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate',
        total_nav     numeric(20,2) PATH 'Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=/FundsXML4/Funds/Fund/Currency]'
     ) f;

-- position -------------------------------------------------------------------
INSERT INTO position (document_id, unique_id, isin, currency,
                       value_fund_ccy, percentage, kind, kind_qty)
SELECT s.document_id, p.unique_id, p.isin, p.currency,
       p.value_fund_ccy, p.percentage, p.kind, p.kind_qty
FROM fundsxml_stage s,
     LATERAL (SELECT (xpath('/FundsXML4/Funds/Fund/Currency/text()',
                            s.doc))[1]::text AS ccy) c,
     XMLTABLE('/FundsXML4/Funds/Fund/FundDynamicData/Portfolios/Portfolio/Positions/Position'
        PASSING s.doc COLUMNS
        unique_id      text          PATH 'UniqueID',
        isin           text          PATH 'Identifiers/ISIN',
        currency       text          PATH 'Currency',
        value_fund_ccy numeric(20,2) PATH 'TotalValue/Amount[1]',
        percentage     numeric(9,4)  PATH 'TotalPercentage',
        kind           text          PATH 'local-name(Equity|Bond|ShareClass|Warrant|Certificate|Option|Future|FXForward|Swap|Repo|RealEstate|CallMoney)',
        kind_qty       numeric(28,6) PATH '(Equity/Units|Bond/Nominal|ShareClass/Shares|Warrant/Units|Certificate/Units|Option/Contracts|Future/Contracts)[1]'
     ) p;

-- asset and share_class follow the same XMLTABLE pattern over
-- /FundsXML4/AssetMasterData/Asset and
-- /FundsXML4/Funds/Fund/SingleFund/ShareClasses/ShareClass respectively.
