-- PostgreSQL -> FundsXML (code reference; no DB is provisioned in this repo).
--
-- SQL/XML publishing with xmlelement/xmlagg/xmlattributes. Produces the same
-- FundsXML 4.2.9 positions shape the Python reference emits (XSD-valid).
-- Parameter :doc = fund.document_id.

SELECT xmlelement(name "FundsXML4",
         xmlattributes('http://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd'
                       AS "xsi:noNamespaceSchemaLocation"),
         xmlelement(name "ControlData",
           xmlelement(name "UniqueDocumentID", f.document_id),
           xmlelement(name "DocumentGenerated", '2025-10-02T00:00:00'),
           CASE WHEN f.fxml_version IS NOT NULL
                THEN xmlelement(name "Version", f.fxml_version) END,
           xmlelement(name "ContentDate", f.content_date),
           xmlelement(name "DataSupplier",
             xmlelement(name "SystemCountry",'AT'),
             xmlelement(name "Short",'EURAM'),
             xmlelement(name "Name",'Erste Asset Management GmbH'),
             xmlelement(name "Type",'Asset Manager')),
           xmlelement(name "DataOperation",'INITIAL')),
         xmlelement(name "Funds",
           xmlelement(name "Fund",
             xmlelement(name "Identifiers",
               xmlelement(name "LEI", f.lei)),
             xmlelement(name "Names",
               xmlelement(name "OfficialName", f.official_name)),
             xmlelement(name "Currency", f.currency),
             xmlelement(name "SingleFundFlag",'true'),
             xmlelement(name "FundDynamicData",
               xmlelement(name "TotalAssetValues",
                 xmlelement(name "TotalAssetValue",
                   xmlelement(name "NavDate", f.nav_date),
                   xmlelement(name "TotalAssetNature",'OFFICIAL'),
                   xmlelement(name "TotalNetAssetValue",
                     xmlelement(name "Amount",
                       xmlattributes(f.currency AS "ccy"),
                       to_char(f.total_nav,'FM999999999990.00'))))),
               xmlelement(name "Portfolios",
                 xmlelement(name "Portfolio",
                   xmlelement(name "NavDate", f.nav_date),
                   xmlelement(name "Positions",
                     (SELECT xmlagg(
                        xmlelement(name "Position",
                          xmlelement(name "UniqueID", p.unique_id),
                          CASE WHEN p.isin IS NOT NULL THEN
                            xmlelement(name "Identifiers",
                              xmlelement(name "ISIN", p.isin)) END,
                          xmlelement(name "Currency", p.currency),
                          xmlelement(name "TotalValue",
                            xmlelement(name "Amount",
                              xmlattributes(f.currency AS "ccy"),
                              to_char(p.value_fund_ccy,'FM999999999990.00'))),
                          xmlelement(name "TotalPercentage",
                            to_char(p.percentage,'FM990.00')),
                          xmlelement(name p.kind)) ORDER BY p.unique_id)
                      FROM position p WHERE p.document_id = f.document_id))))))
       )
FROM fund f
WHERE f.document_id = :doc;

-- For brevity the position class element is emitted empty; add the quantity
-- child (Units/Nominal/Shares/Contracts from position.kind_qty) exactly as the
-- Python reference does to keep Equity/Bond/ShareClass/... schema-valid.
