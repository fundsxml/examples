-- FundsXML -> Oracle (code reference; no DB is provisioned in this repo).
--
-- Strategy: stage in an XMLType column, shred with XMLTABLE. FundsXML 4.x has
-- no namespace. Schema: ../ddl/schema.sql with VARCHAR2/NUMBER types.

CREATE TABLE fundsxml_stage (
    document_id VARCHAR2(128) PRIMARY KEY,
    doc         XMLTYPE NOT NULL
);

-- Load (SQL*Plus / SQLcl): use a BFILE or :bind variable, e.g.
--   INSERT INTO fundsxml_stage(document_id, doc)
--   VALUES ( :doc.extract('/FundsXML4/ControlData/UniqueDocumentID/text()')
--                 .getStringVal(), XMLTYPE(:doc) );

INSERT INTO fund (document_id, lei, official_name, currency,
                  content_date, nav_date, total_nav, fxml_version)
SELECT s.document_id, f.lei, f.official_name, f.currency,
       TO_DATE(f.content_date,'YYYY-MM-DD'),
       TO_DATE(f.nav_date,'YYYY-MM-DD'), f.total_nav, f.fxml_version
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4' PASSING s.doc COLUMNS
        lei           VARCHAR2(20)  PATH 'Funds/Fund/Identifiers/LEI',
        official_name VARCHAR2(256) PATH 'Funds/Fund/Names/OfficialName',
        currency      VARCHAR2(3)   PATH 'Funds/Fund/Currency',
        content_date  VARCHAR2(10)  PATH 'ControlData/ContentDate',
        fxml_version  VARCHAR2(16)  PATH 'ControlData/Version',
        nav_date      VARCHAR2(10)  PATH 'Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate',
        total_nav     NUMBER        PATH 'Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy=/FundsXML4/Funds/Fund/Currency]'
     ) f;

INSERT INTO position (document_id, unique_id, isin, currency,
                       value_fund_ccy, percentage, kind, kind_qty)
SELECT s.document_id, p.unique_id, p.isin, p.currency,
       p.value_fund_ccy, p.percentage, p.kind, p.kind_qty
FROM fundsxml_stage s,
     XMLTABLE('/FundsXML4/Funds/Fund/FundDynamicData/Portfolios/Portfolio/Positions/Position'
        PASSING s.doc COLUMNS
        unique_id      VARCHAR2(256) PATH 'UniqueID',
        isin           VARCHAR2(12)  PATH 'Identifiers/ISIN',
        currency       VARCHAR2(3)   PATH 'Currency',
        value_fund_ccy NUMBER        PATH 'TotalValue/Amount[1]',
        percentage     NUMBER        PATH 'TotalPercentage',
        kind           VARCHAR2(16)  PATH 'name(*[local-name()=("Equity","Bond","ShareClass","Warrant","Certificate","Option","Future","FXForward","Swap","Repo","RealEstate","CallMoney")][1])',
        kind_qty       NUMBER        PATH '(Equity/Units|Bond/Nominal|ShareClass/Shares|Warrant/Units|Certificate/Units|Option/Contracts|Future/Contracts)[1]'
     ) p;

-- asset / share_class: same XMLTABLE pattern over their node sets.
