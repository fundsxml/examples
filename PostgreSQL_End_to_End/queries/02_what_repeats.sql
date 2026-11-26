-- Everything repeats: rows per file, and the NAVs of one share class on one day.
SELECT d.unique_document_id,
       (SELECT count(DISTINCT fund_id) FROM nav n WHERE n.delivery_id = d.delivery_id)          AS funds,
       (SELECT count(DISTINCT nav_date) FROM price p WHERE p.delivery_id = d.delivery_id)       AS nav_dates,
       (SELECT count(*) FROM price p WHERE p.delivery_id = d.delivery_id)                       AS prices,
       (SELECT count(*) FROM nav n WHERE n.delivery_id = d.delivery_id)                         AS navs,
       (SELECT count(*) FROM portfolio p WHERE p.delivery_id = d.delivery_id)                   AS portfolios,
       (SELECT count(*) FROM position x JOIN portfolio p USING (portfolio_id)
         WHERE p.delivery_id = d.delivery_id)                                                   AS positions
FROM delivery d
WHERE d.data_operation = 'INITIAL'
ORDER BY d.delivery_id;

\echo 'Net assets of the CHF class on 2025-11-05: two natures, two currencies'
SELECT n.nav_date, n.nature, n.amount, n.currency, n.is_share_class_ccy, n.is_fund_ccy, n.shares_outstanding
FROM nav n JOIN share_class s USING (share_class_id)
WHERE s.isin = 'ATXMPLF03032' AND n.nav_date = '2025-11-05' AND n.replaced_by_delivery_id IS NULL
ORDER BY n.nature, n.currency DESC;
