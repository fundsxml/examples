-- FundsXML -> Oracle, MULTI-FUND (code reference; no DB is provisioned).
--
-- Pattern: stage in an XMLType column; nested XMLTABLE with FOR ORDINALITY
-- gives fund_seq / portfolio_seq / position_seq (PASSING the parent node into
-- the inner XMLTABLE). FundsXML 4.x has no XML namespace -> bare element
-- names. Full column list: ../ddl/schema.sql; the runnable Python/Java/
-- JavaScript/C# programs implement the same mapping end to end.

CREATE TABLE fundsxml_stage (
    document_id VARCHAR2(128) PRIMARY KEY,
    doc         XMLTYPE NOT NULL
);

INSERT INTO document
SELECT s.document_id, c.generated, c.version,
       TO_DATE(c.content_date,'YYYY-MM-DD'), c.data_operation,
       c.supplier_country, c.supplier_short, c.supplier_name, c.supplier_type
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/ControlData' PASSING s.doc COLUMNS
        generated        VARCHAR2(32)  PATH 'DocumentGenerated',
        version          VARCHAR2(16)  PATH 'Version',
        content_date     VARCHAR2(10)  PATH 'ContentDate',
        data_operation   VARCHAR2(16)  PATH 'DataOperation',
        supplier_country VARCHAR2(2)   PATH 'DataSupplier/SystemCountry',
        supplier_short   VARCHAR2(64)  PATH 'DataSupplier/Short',
        supplier_name    VARCHAR2(256) PATH 'DataSupplier/Name',
        supplier_type    VARCHAR2(64)  PATH 'DataSupplier/Type') c;

INSERT INTO fund
SELECT s.document_id, f.fund_seq, f.lei, f.official_name, f.currency,
       f.single_fund_flag, TO_DATE(f.nav_date,'YYYY-MM-DD'), f.total_nav
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/Funds/Fund' PASSING s.doc COLUMNS
        fund_seq         FOR ORDINALITY,
        lei              VARCHAR2(20)  PATH 'Identifiers/LEI',
        official_name    VARCHAR2(256) PATH 'Names/OfficialName',
        currency         VARCHAR2(3)   PATH 'Currency',
        single_fund_flag VARCHAR2(8)   PATH 'SingleFundFlag',
        nav_date         VARCHAR2(10)  PATH 'FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate',
        total_nav        NUMBER        PATH 'FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=ancestor::Fund/Currency]') f;

-- Positions: outer XMLTABLE over Fund (fund_seq + the Fund node), middle over
-- Portfolio (portfolio_seq + node), inner over Position (position_seq).
INSERT INTO position
SELECT s.document_id, fu.fund_seq, pf.portfolio_seq, pos.position_seq,
       pos.unique_id, pos.isin, pos.currency, pos.value_fund_ccy,
       pos.percentage, pos.kind, pos.kind_qty
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/Funds/Fund' PASSING s.doc
        COLUMNS fund_seq FOR ORDINALITY,
                fund_node XMLTYPE PATH '.') fu,
     XMLTABLE('FundDynamicData/Portfolios/Portfolio' PASSING fu.fund_node
        COLUMNS portfolio_seq FOR ORDINALITY,
                port_node XMLTYPE PATH '.') pf,
     XMLTABLE('Positions/Position' PASSING pf.port_node COLUMNS
        position_seq   FOR ORDINALITY,
        unique_id      VARCHAR2(256) PATH 'UniqueID',
        isin           VARCHAR2(12)  PATH 'Identifiers/ISIN',
        currency       VARCHAR2(3)   PATH 'Currency',
        value_fund_ccy NUMBER        PATH 'TotalValue/Amount[1]',
        percentage     NUMBER        PATH 'TotalPercentage',
        kind           VARCHAR2(16)  PATH 'name((Equity|Bond|ShareClass|Warrant|Certificate|Option|Future|FXForward|Swap|Repo|RealEstate|CallMoney)[1])',
        kind_qty       NUMBER        PATH '(Equity/Units|Bond/Nominal|ShareClass/Shares|Warrant/Units|Certificate/Units|Option/Contracts|Future/Contracts)[1]') pos;

-- portfolio, share_class (per fund) and asset (document-scoped) follow the
-- same nested-XMLTABLE pattern.
