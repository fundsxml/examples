-- FundsXML -> PostgreSQL, MULTI-FUND (code reference; no DB is provisioned).
--
-- Pattern: stage the document in a native `xml` column, then shred with
-- nested XMLTABLE. The OUTER XMLTABLE emits one row per <Fund> and uses
-- FOR ORDINALITY to get fund_seq; inner XMLTABLEs (PASSING the fund/portfolio
-- node) do the same for portfolios and positions. FundsXML 4.x has no XML
-- namespace, so XPath uses bare element names. The runnable Python/Java/
-- JavaScript/C# examples implement this exact mapping end to end; see
-- ../ddl/schema.sql for the full column list.

CREATE TABLE IF NOT EXISTS fundsxml_stage (
    document_id text PRIMARY KEY,
    doc         xml NOT NULL
);

-- document (ControlData) ------------------------------------------------------
INSERT INTO document
SELECT s.document_id, c.*
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/ControlData' PASSING s.doc COLUMNS
        generated        text PATH 'DocumentGenerated',
        version          text PATH 'Version',
        content_date     date PATH 'ContentDate',
        data_operation   text PATH 'DataOperation',
        supplier_country text PATH 'DataSupplier/SystemCountry',
        supplier_short   text PATH 'DataSupplier/Short',
        supplier_name    text PATH 'DataSupplier/Name',
        supplier_type    text PATH 'DataSupplier/Type') c;

-- fund (one row per <Fund>; fund_seq via FOR ORDINALITY) ---------------------
INSERT INTO fund
SELECT s.document_id, f.fund_seq, f.lei, f.official_name, f.currency,
       f.single_fund_flag, f.nav_date, f.total_nav
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/Funds/Fund' PASSING s.doc COLUMNS
        fund_seq         FOR ORDINALITY,
        lei              text          PATH 'Identifiers/LEI',
        official_name    text          PATH 'Names/OfficialName',
        currency         text          PATH 'Currency',
        single_fund_flag text          PATH 'SingleFundFlag',
        nav_date         date          PATH 'FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate',
        total_nav        numeric(20,2) PATH 'FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=ancestor::Fund/Currency]') f;

-- portfolio + position (nested: portfolios per fund, positions per portfolio)
INSERT INTO portfolio
SELECT s.document_id, fu.fund_seq, pf.portfolio_seq, pf.nav_date
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/Funds/Fund' PASSING s.doc COLUMNS
        fund_seq  FOR ORDINALITY,
        fund_node xml PATH '.') fu,
     XMLTABLE('FundDynamicData/Portfolios/Portfolio' PASSING fu.fund_node
        COLUMNS portfolio_seq FOR ORDINALITY,
                nav_date      date PATH 'NavDate') pf;

INSERT INTO position
SELECT s.document_id, fu.fund_seq, pf.portfolio_seq, pos.position_seq,
       pos.unique_id, pos.isin, pos.currency, pos.value_fund_ccy,
       pos.percentage, pos.kind, pos.kind_qty
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/Funds/Fund' PASSING s.doc COLUMNS
        fund_seq FOR ORDINALITY, ccy text PATH 'Currency',
        fund_node xml PATH '.') fu,
     XMLTABLE('FundDynamicData/Portfolios/Portfolio' PASSING fu.fund_node
        COLUMNS portfolio_seq FOR ORDINALITY, port_node xml PATH '.') pf,
     XMLTABLE('Positions/Position' PASSING pf.port_node COLUMNS
        position_seq   FOR ORDINALITY,
        unique_id      text          PATH 'UniqueID',
        isin           text          PATH 'Identifiers/ISIN',
        currency       text          PATH 'Currency',
        value_fund_ccy numeric(20,2) PATH 'TotalValue/Amount[1]',
        percentage     numeric(9,4)  PATH 'TotalPercentage',
        kind           text          PATH 'local-name(Equity|Bond|ShareClass|Warrant|Certificate|Option|Future|FXForward|Swap|Repo|RealEstate|CallMoney)',
        kind_qty       numeric(28,6) PATH '(Equity/Units|Bond/Nominal|ShareClass/Shares|Warrant/Units|Certificate/Units|Option/Contracts|Future/Contracts)[1]') pos;

-- share_class (per fund) and asset (document-scoped) follow the same nested
-- XMLTABLE pattern over SingleFund/ShareClasses/ShareClass and
-- /FundsXML4/AssetMasterData/Asset respectively.
