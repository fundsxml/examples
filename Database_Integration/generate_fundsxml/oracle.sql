-- Oracle -> FundsXML (code reference; no DB is provisioned in this repo).
--
-- SQL/XML publishing: XMLElement / XMLAgg / XMLAttributes. Same FundsXML 4.2.9
-- positions shape as the Python reference. Bind :doc = fund.document_id.

SELECT XMLElement("FundsXML4",
         XMLAttributes(
           'http://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd'
             AS "xsi:noNamespaceSchemaLocation"),
         XMLElement("ControlData",
           XMLElement("UniqueDocumentID", f.document_id),
           XMLElement("DocumentGenerated", '2025-10-02T00:00:00'),
           CASE WHEN f.fxml_version IS NOT NULL
                THEN XMLElement("Version", f.fxml_version) END,
           XMLElement("ContentDate", TO_CHAR(f.content_date,'YYYY-MM-DD')),
           XMLElement("DataSupplier",
             XMLElement("SystemCountry",'AT'),
             XMLElement("Short",'EURAM'),
             XMLElement("Name",'Erste Asset Management GmbH'),
             XMLElement("Type",'Asset Manager')),
           XMLElement("DataOperation",'INITIAL')),
         XMLElement("Funds",
           XMLElement("Fund",
             XMLElement("Identifiers", XMLElement("LEI", f.lei)),
             XMLElement("Names", XMLElement("OfficialName", f.official_name)),
             XMLElement("Currency", f.currency),
             XMLElement("SingleFundFlag",'true'),
             XMLElement("FundDynamicData",
               XMLElement("TotalAssetValues",
                 XMLElement("TotalAssetValue",
                   XMLElement("NavDate", TO_CHAR(f.nav_date,'YYYY-MM-DD')),
                   XMLElement("TotalAssetNature",'OFFICIAL'),
                   XMLElement("TotalNetAssetValue",
                     XMLElement("Amount",
                       XMLAttributes(f.currency AS "ccy"),
                       TO_CHAR(f.total_nav,'FM999999999990.00'))))),
               XMLElement("Portfolios",
                 XMLElement("Portfolio",
                   XMLElement("NavDate", TO_CHAR(f.nav_date,'YYYY-MM-DD')),
                   XMLElement("Positions",
                     (SELECT XMLAgg(
                        XMLElement("Position",
                          XMLElement("UniqueID", p.unique_id),
                          XMLElement("Currency", p.currency),
                          XMLElement("TotalValue",
                            XMLElement("Amount",
                              XMLAttributes(f.currency AS "ccy"),
                              TO_CHAR(p.value_fund_ccy,'FM999999999990.00'))),
                          XMLElement("TotalPercentage",
                            TO_CHAR(p.percentage,'FM990.00')),
                          XMLElement(EVALNAME p.kind))
                        ORDER BY p.unique_id)
                      FROM position p
                      WHERE p.document_id = f.document_id)))))))
       ).getClobVal()
FROM fund f
WHERE f.document_id = :doc;

-- As with the Postgres example, add the quantity child per kind
-- (position.kind_qty) to keep Equity/Bond/ShareClass/... schema-valid.
