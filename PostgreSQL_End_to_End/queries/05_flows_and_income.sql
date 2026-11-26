-- Transactions in their four places, October 2025, per fund.
SELECT f.name AS fund, x.place, x.kind, count(*) AS rows, sum(x.amount) AS amount, x.currency
FROM (
    SELECT s.fund_id, 'share class: flows' AS place, fl.flow_type AS kind, fl.value AS amount, fl.currency
    FROM sc_flow fl JOIN share_class s USING (share_class_id) WHERE fl.replaced_by_delivery_id IS NULL
    UNION ALL
    SELECT s.fund_id, 'share class: distributions', 'per share', d.gross_per_share, d.currency
    FROM distribution d JOIN share_class s USING (share_class_id) WHERE d.replaced_by_delivery_id IS NULL
    UNION ALL
    SELECT p.fund_id, 'portfolio: trades', t.kind, t.settlement_amount, t.settlement_ccy
    FROM trade t JOIN portfolio p USING (portfolio_id) WHERE p.replaced_by_delivery_id IS NULL
    UNION ALL
    SELECT p.fund_id, 'portfolio: income', e.kind, e.value, e.currency
    FROM earning e JOIN portfolio p USING (portfolio_id) WHERE p.replaced_by_delivery_id IS NULL
) x JOIN fund f USING (fund_id)
WHERE f.name LIKE '%Global Equity%'
GROUP BY f.name, x.place, x.kind, x.currency
ORDER BY x.place, x.kind, x.currency;
