-- FundsXML -> SQL Server, MULTI-FUND (code reference; no DB is provisioned).
--
-- Pattern: stage in an `xml` column; .nodes() shreds the repeating elements.
-- ROW_NUMBER() OVER (ORDER BY (SELECT 1)) over the .nodes() rowset reproduces
-- document order -> fund_seq / portfolio_seq / position_seq. CROSS APPLY
-- chains Fund -> Portfolio -> Position so every fund/portfolio is visited.
-- FundsXML 4.x has no XML namespace. Full columns: ../ddl/schema.sql; the
-- runnable Python/Java/JavaScript/C# programs implement the same mapping.

CREATE TABLE fundsxml_stage (
    document_id VARCHAR(128) PRIMARY KEY,
    doc         XML NOT NULL
);

INSERT INTO document
SELECT s.document_id,
       d.value('(DocumentGenerated)[1]','varchar(32)'),
       d.value('(Version)[1]','varchar(16)'),
       d.value('(ContentDate)[1]','date'),
       d.value('(DataOperation)[1]','varchar(16)'),
       d.value('(DataSupplier/SystemCountry)[1]','char(2)'),
       d.value('(DataSupplier/Short)[1]','varchar(64)'),
       d.value('(DataSupplier/Name)[1]','varchar(256)'),
       d.value('(DataSupplier/Type)[1]','varchar(64)')
FROM fundsxml_stage s
CROSS APPLY s.doc.nodes('/FundsXML4/ControlData') AS t(d);

-- fund_seq from the position of each <Fund> in document order.
INSERT INTO fund
SELECT s.document_id,
       ROW_NUMBER() OVER (ORDER BY (SELECT 1)) AS fund_seq,
       f.value('(Identifiers/LEI)[1]','varchar(20)'),
       f.value('(Names/OfficialName)[1]','varchar(256)'),
       f.value('(Currency)[1]','char(3)'),
       f.value('(SingleFundFlag)[1]','varchar(8)'),
       f.value('(FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate)[1]','date'),
       f.value('(FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount)[1]','decimal(20,2)')
FROM fundsxml_stage s
CROSS APPLY s.doc.nodes('/FundsXML4/Funds/Fund') AS t(f);

-- Positions: number funds, then portfolios within each fund, then positions
-- within each portfolio (CROSS APPLY carries the parent node down).
INSERT INTO position
SELECT s.document_id, fx.fund_seq, px.portfolio_seq,
       ROW_NUMBER() OVER (PARTITION BY fx.fund_seq, px.portfolio_seq
                          ORDER BY (SELECT 1)) AS position_seq,
       q.value('(UniqueID)[1]','varchar(256)'),
       q.value('(Identifiers/ISIN)[1]','char(12)'),
       q.value('(Currency)[1]','char(3)'),
       q.value('(TotalValue/Amount)[1]','decimal(20,2)'),
       q.value('(TotalPercentage)[1]','decimal(9,4)'),
       q.value('local-name((Equity|Bond|ShareClass|Warrant|Certificate|Option|Future|FXForward|Swap|Repo|RealEstate|CallMoney)[1])','varchar(16)'),
       q.value('(Equity/Units|Bond/Nominal|ShareClass/Shares|Warrant/Units|Certificate/Units|Option/Contracts|Future/Contracts)[1]','decimal(28,6)')
FROM fundsxml_stage s
CROSS APPLY (SELECT f.f, ROW_NUMBER() OVER (ORDER BY (SELECT 1)) fund_seq
             FROM s.doc.nodes('/FundsXML4/Funds/Fund') AS f(f)) fx
CROSS APPLY (SELECT p.p, ROW_NUMBER() OVER (ORDER BY (SELECT 1)) portfolio_seq
             FROM fx.f.nodes('FundDynamicData/Portfolios/Portfolio') AS p(p)) px
CROSS APPLY px.p.nodes('Positions/Position') AS t(q);

-- portfolio, share_class (per fund) and asset (document-scoped) follow the
-- same numbered CROSS APPLY pattern.
