-- FundsXML -> SQL Server (code reference; no DB is provisioned in this repo).
--
-- Strategy: stage in an `xml` column, shred with .nodes()/.value(). FundsXML
-- 4.x has no namespace. Schema: ../ddl/schema.sql.

CREATE TABLE fundsxml_stage (
    document_id VARCHAR(128) PRIMARY KEY,
    doc         XML NOT NULL
);

-- Load: read the file with OPENROWSET(BULK ... SINGLE_CLOB) then
--   INSERT INTO fundsxml_stage(document_id, doc)
--   SELECT x.value('(/FundsXML4/ControlData/UniqueDocumentID)[1]','varchar(128)'),
--          x
--   FROM (SELECT CAST(BulkColumn AS XML) AS x
--         FROM OPENROWSET(BULK '...Mixed-Fund_Positions.xml',
--                         SINGLE_CLOB) r) src;

INSERT INTO fund (document_id, lei, official_name, currency,
                  content_date, nav_date, total_nav, fxml_version)
SELECT s.document_id,
       d.value('(Funds/Fund/Identifiers/LEI)[1]','varchar(20)'),
       d.value('(Funds/Fund/Names/OfficialName)[1]','varchar(256)'),
       d.value('(Funds/Fund/Currency)[1]','char(3)'),
       d.value('(ControlData/ContentDate)[1]','date'),
       d.value('(Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate)[1]','date'),
       d.value('(Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount)[1]','decimal(20,2)'),
       d.value('(ControlData/Version)[1]','varchar(16)')
FROM fundsxml_stage s
CROSS APPLY s.doc.nodes('/FundsXML4') AS t(d);

INSERT INTO position (document_id, unique_id, isin, currency,
                       value_fund_ccy, percentage, kind, kind_qty)
SELECT s.document_id,
       p.value('(UniqueID)[1]','varchar(256)'),
       p.value('(Identifiers/ISIN)[1]','char(12)'),
       p.value('(Currency)[1]','char(3)'),
       p.value('(TotalValue/Amount)[1]','decimal(20,2)'),
       p.value('(TotalPercentage)[1]','decimal(9,4)'),
       p.value('local-name((Equity|Bond|ShareClass|Warrant|Certificate|Option|Future|FXForward|Swap|Repo|RealEstate|CallMoney)[1])','varchar(16)'),
       p.value('(Equity/Units|Bond/Nominal|ShareClass/Shares|Warrant/Units|Certificate/Units|Option/Contracts|Future/Contracts)[1]','decimal(28,6)')
FROM fundsxml_stage s
CROSS APPLY s.doc.nodes(
   '/FundsXML4/Funds/Fund/FundDynamicData/Portfolios/Portfolio/Positions/Position'
) AS t(p);

-- asset / share_class: same CROSS APPLY .nodes() / .value() pattern.
