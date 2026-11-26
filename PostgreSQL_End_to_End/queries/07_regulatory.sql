-- Regulatory templates: key fields as columns, the rest read from the XML when needed.
SELECT template, template_version, isin, reference_date, ongoing_costs, sfdr_product_type, considers_pai,
       tpt_positions,
       (xpath('/*/TargetMarket/InvestorType/Retail/text()', content))[1]::text AS emt_retail
FROM regulatory_report
WHERE replaced_by_delivery_id IS NULL
ORDER BY template, isin;
