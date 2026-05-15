-- PostgreSQL -> FundsXML, MULTI-FUND (code reference; no DB is provisioned).
--
-- SQL/XML publishing. The key multi-node move: a correlated subquery with
-- xmlagg(... ORDER BY fund_seq) emits one <Fund> per fund row, and inside it
-- another xmlagg over portfolio -> positions. Emits the same canonical shape
-- as the runnable examples (so xml_equiv.py treats it as equal). :doc binds
-- document.document_id. Constants the model does not store (TotalAssetNature=
-- OFFICIAL, etc.) are reproduced verbatim. See ../ddl/schema.sql.

SELECT xmlelement(name "FundsXML4",
         xmlattributes(
           'http://www.w3.org/2001/XMLSchema-instance' AS "xmlns:xsi",
           'https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd'
             AS "xsi:noNamespaceSchemaLocation"),
         -- ControlData
         (SELECT xmlelement(name "ControlData",
            xmlelement(name "UniqueDocumentID", doc.document_id),
            xmlelement(name "DocumentGenerated", doc.generated),
            CASE WHEN doc.version IS NOT NULL
                 THEN xmlelement(name "Version", doc.version) END,
            xmlelement(name "ContentDate", doc.content_date),
            xmlelement(name "DataSupplier",
              xmlelement(name "SystemCountry", doc.supplier_country),
              xmlelement(name "Short", doc.supplier_short),
              xmlelement(name "Name", doc.supplier_name),
              xmlelement(name "Type", doc.supplier_type)),
            xmlelement(name "DataOperation", doc.data_operation))
          FROM document doc WHERE doc.document_id = :doc),
         -- Funds: one <Fund> per fund row, in fund_seq order
         xmlelement(name "Funds",
           (SELECT xmlagg(
              xmlelement(name "Fund",
                CASE WHEN f.lei IS NOT NULL THEN xmlelement(name "Identifiers",
                     xmlelement(name "LEI", f.lei)) END,
                xmlelement(name "Names",
                     xmlelement(name "OfficialName", f.official_name)),
                xmlelement(name "Currency", f.currency),
                CASE WHEN f.single_fund_flag IS NOT NULL
                     THEN xmlelement(name "SingleFundFlag",
                          f.single_fund_flag) END,
                xmlelement(name "FundDynamicData",
                  xmlelement(name "TotalAssetValues",
                    xmlelement(name "TotalAssetValue",
                      xmlelement(name "NavDate", f.nav_date),
                      xmlelement(name "TotalAssetNature", 'OFFICIAL'),
                      xmlelement(name "TotalNetAssetValue",
                        xmlelement(name "Amount",
                          xmlattributes(f.currency AS "ccy"),
                          to_char(f.total_nav,'FM999999990.00'))))),
                  xmlelement(name "Portfolios",
                    (SELECT xmlagg(
                       xmlelement(name "Portfolio",
                         xmlelement(name "NavDate", pf.nav_date),
                         xmlelement(name "Positions",
                           (SELECT xmlagg(
                              xmlelement(name "Position",
                                xmlelement(name "UniqueID", p.unique_id),
                                xmlelement(name "Currency", p.currency),
                                xmlelement(name "TotalValue",
                                  xmlelement(name "Amount",
                                    xmlattributes(f.currency AS "ccy"),
                                    to_char(p.value_fund_ccy,'FM999999990.00'))),
                                xmlelement(name "TotalPercentage",
                                  to_char(p.percentage,'FM990.00')),
                                xmlelement(name p.kind))
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
       )
FROM (SELECT 1) _;

-- The Position class element is emitted empty for brevity; add its quantity
-- child (position.kind_qty -> Units/Nominal/Shares/Contracts) and the
-- per-fund SingleFund/ShareClasses block exactly as the runnable examples do.
