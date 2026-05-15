-- SQL Server -> FundsXML (code reference; no DB is provisioned in this repo).
--
-- FOR XML PATH with nested subqueries. Same FundsXML 4.2.9 positions shape as
-- the Python reference. @doc = fund.document_id.

DECLARE @doc varchar(128) = 'FUNDSXML_FILE_1';

SELECT
  'http://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd'
    AS [@xsi:noNamespaceSchemaLocation],
  f.document_id              AS [ControlData/UniqueDocumentID],
  '2025-10-02T00:00:00'      AS [ControlData/DocumentGenerated],
  f.fxml_version             AS [ControlData/Version],
  CONVERT(varchar(10), f.content_date, 23) AS [ControlData/ContentDate],
  'AT'    AS [ControlData/DataSupplier/SystemCountry],
  'EURAM' AS [ControlData/DataSupplier/Short],
  'Erste Asset Management GmbH' AS [ControlData/DataSupplier/Name],
  'Asset Manager' AS [ControlData/DataSupplier/Type],
  'INITIAL' AS [ControlData/DataOperation],
  f.lei           AS [Funds/Fund/Identifiers/LEI],
  f.official_name AS [Funds/Fund/Names/OfficialName],
  f.currency      AS [Funds/Fund/Currency],
  'true'          AS [Funds/Fund/SingleFundFlag],
  CONVERT(varchar(10), f.nav_date, 23)
    AS [Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate],
  'OFFICIAL'
    AS [Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalAssetNature],
  f.currency
    AS [Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount/@ccy],
  CONVERT(varchar(32), f.total_nav)
    AS [Funds/Fund/FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount],
  (SELECT
       p.unique_id AS [UniqueID],
       p.currency  AS [Currency],
       f.currency  AS [TotalValue/Amount/@ccy],
       CONVERT(varchar(32), p.value_fund_ccy) AS [TotalValue/Amount],
       CONVERT(varchar(16), p.percentage)     AS [TotalPercentage]
       -- plus the kind element (+ quantity child) — see note below
   FROM position p
   WHERE p.document_id = f.document_id
   ORDER BY p.unique_id
   FOR XML PATH('Position'), TYPE)
     AS [Funds/Fund/FundDynamicData/Portfolios/Portfolio/Positions]
FROM fund f
WHERE f.document_id = @doc
FOR XML PATH('FundsXML4');

-- The position class element (Equity/Bond/.../with its Units/Nominal/Shares/
-- Contracts child from position.kind_qty) is added with a correlated
-- FOR XML PATH subquery per row — emitted dynamically because the element name
-- itself varies; see the Python reference for the exact mapping.
