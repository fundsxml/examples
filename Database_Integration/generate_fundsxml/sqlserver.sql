-- SQL Server -> FundsXML, MULTI-FUND (code reference; no DB is provisioned).
--
-- FOR XML PATH with nested correlated subqueries. Multi-node essence: the
-- outer FOR XML PATH('Fund') over `fund` (ORDER BY fund_seq) yields many
-- <Fund>; a correlated FOR XML PATH('Portfolio') over `portfolio`, and inside
-- it FOR XML PATH('Position') over `position`, give the nested repetition.
-- Same canonical shape as the runnable examples (xml_equiv.py-equal).
-- @doc = document.document_id. Full mapping: ../ddl/schema.sql.

DECLARE @doc varchar(128) = 'FUNDSXML_MULTI_1';

SELECT
  'http://www.w3.org/2001/XMLSchema-instance' AS [@xmlns:xsi],
  'https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd'
    AS [@xsi:noNamespaceSchemaLocation],
  (SELECT d.document_id AS [UniqueDocumentID],
          d.generated   AS [DocumentGenerated],
          d.version     AS [Version],
          CONVERT(varchar(10), d.content_date, 23) AS [ContentDate],
          d.supplier_country AS [DataSupplier/SystemCountry],
          d.supplier_short   AS [DataSupplier/Short],
          d.supplier_name    AS [DataSupplier/Name],
          d.supplier_type    AS [DataSupplier/Type],
          d.data_operation   AS [DataOperation]
   FROM document d WHERE d.document_id=@doc
   FOR XML PATH('ControlData'), TYPE),
  (SELECT
     f.lei           AS [Identifiers/LEI],
     f.official_name AS [Names/OfficialName],
     f.currency      AS [Currency],
     f.single_fund_flag AS [SingleFundFlag],
     CONVERT(varchar(10), f.nav_date, 23)
       AS [FundDynamicData/TotalAssetValues/TotalAssetValue/NavDate],
     'OFFICIAL'
       AS [FundDynamicData/TotalAssetValues/TotalAssetValue/TotalAssetNature],
     f.currency
       AS [FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount/@ccy],
     CONVERT(varchar(32), f.total_nav)
       AS [FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount],
     (SELECT CONVERT(varchar(10), pf.nav_date, 23) AS [NavDate],
        (SELECT p.unique_id AS [UniqueID], p.currency AS [Currency],
                f.currency  AS [TotalValue/Amount/@ccy],
                CONVERT(varchar(32), p.value_fund_ccy) AS [TotalValue/Amount],
                CONVERT(varchar(16), p.percentage)     AS [TotalPercentage]
         FROM position p
         WHERE p.document_id=f.document_id AND p.fund_seq=f.fund_seq
           AND p.portfolio_seq=pf.portfolio_seq
         ORDER BY p.position_seq
         FOR XML PATH('Position'), TYPE) AS [Positions]
      FROM portfolio pf
      WHERE pf.document_id=f.document_id AND pf.fund_seq=f.fund_seq
      ORDER BY pf.portfolio_seq
      FOR XML PATH('Portfolio'), TYPE) AS [FundDynamicData/Portfolios]
   FROM fund f WHERE f.document_id=@doc
   ORDER BY f.fund_seq
   FOR XML PATH('Fund'), ROOT('Funds'), TYPE)
FOR XML PATH('FundsXML4');

-- The Position class element (+ its quantity child from position.kind_qty)
-- and the per-fund SingleFund/ShareClasses block are added with further
-- correlated FOR XML PATH subqueries, exactly as the runnable examples do.
