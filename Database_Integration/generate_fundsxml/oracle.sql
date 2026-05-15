-- Oracle -> FundsXML, MULTI-FUND (code reference; no DB is provisioned).
--
-- SQL/XML publishing with XMLAGG. Multi-node essence: XMLAGG over the fund
-- rows (ORDER BY fund_seq) yields many <Fund>; nested correlated XMLAGG over
-- portfolio then position. Same canonical shape as the runnable examples
-- (xml_equiv.py-equal). :doc = document.document_id. Full per-column mapping:
-- ../ddl/schema.sql and the Python/Java/JavaScript/C# programs.

SELECT XMLELEMENT("FundsXML4",
         XMLATTRIBUTES(
           'http://www.w3.org/2001/XMLSchema-instance' AS "xmlns:xsi",
           'https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd'
             AS "xsi:noNamespaceSchemaLocation"),
         (SELECT XMLELEMENT("ControlData",
            XMLFOREST(d.document_id AS "UniqueDocumentID",
                      d.generated   AS "DocumentGenerated",
                      d.version     AS "Version",
                      TO_CHAR(d.content_date,'YYYY-MM-DD') AS "ContentDate"),
            XMLELEMENT("DataSupplier",
              XMLFOREST(d.supplier_country AS "SystemCountry",
                        d.supplier_short   AS "Short",
                        d.supplier_name    AS "Name",
                        d.supplier_type    AS "Type")),
            XMLELEMENT("DataOperation", d.data_operation))
          FROM document d WHERE d.document_id = :doc),
         XMLELEMENT("Funds",
           (SELECT XMLAGG(
              XMLELEMENT("Fund",
                XMLELEMENT("Identifiers", XMLELEMENT("LEI", f.lei)),
                XMLELEMENT("Names",
                           XMLELEMENT("OfficialName", f.official_name)),
                XMLELEMENT("Currency", f.currency),
                XMLELEMENT("SingleFundFlag", f.single_fund_flag),
                XMLELEMENT("FundDynamicData",
                  XMLELEMENT("TotalAssetValues",
                    XMLELEMENT("TotalAssetValue",
                      XMLFOREST(TO_CHAR(f.nav_date,'YYYY-MM-DD') AS "NavDate",
                                'OFFICIAL' AS "TotalAssetNature"),
                      XMLELEMENT("TotalNetAssetValue",
                        XMLELEMENT("Amount",
                          XMLATTRIBUTES(f.currency AS "ccy"),
                          TO_CHAR(f.total_nav,'FM999999990.00'))))),
                  XMLELEMENT("Portfolios",
                    (SELECT XMLAGG(
                       XMLELEMENT("Portfolio",
                         XMLELEMENT("NavDate",
                           TO_CHAR(pf.nav_date,'YYYY-MM-DD')),
                         XMLELEMENT("Positions",
                           (SELECT XMLAGG(
                              XMLELEMENT("Position",
                                XMLFOREST(p.unique_id AS "UniqueID",
                                          p.currency  AS "Currency"),
                                XMLELEMENT("TotalValue",
                                  XMLELEMENT("Amount",
                                    XMLATTRIBUTES(f.currency AS "ccy"),
                                    TO_CHAR(p.value_fund_ccy,'FM999999990.00'))),
                                XMLELEMENT("TotalPercentage",
                                  TO_CHAR(p.percentage,'FM990.00')),
                                XMLELEMENT(EVALNAME p.kind))
                              ORDER BY p.position_seq)
                            FROM position p
                            WHERE p.document_id=f.document_id
                              AND p.fund_seq=f.fund_seq
                              AND p.portfolio_seq=pf.portfolio_seq)))
                       ORDER BY pf.portfolio_seq)
                     FROM portfolio pf
                     WHERE pf.document_id=f.document_id
                       AND pf.fund_seq=f.fund_seq))))
              ORDER BY f.fund_seq)
            FROM fund f WHERE f.document_id = :doc))
       ).getclobval()
FROM dual;

-- Position class element emitted empty for brevity; add the quantity child
-- (position.kind_qty) and the per-fund SingleFund/ShareClasses block as the
-- runnable examples do.
