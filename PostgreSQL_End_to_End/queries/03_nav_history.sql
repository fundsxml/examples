-- NAV per share of one share class: as known today vs. as known at an earlier point in time.
-- Rows are never overwritten; a correction (AMEND) only sets replaced_by_delivery_id.
-- "Known at" uses the time the sender generated the delivery (ControlData/DocumentGenerated).
--   psql -v isin=ATXMPLF03032 -v as_of='2025-11-06 08:00' -f queries/03_nav_history.sql
\if :{?isin} \else \set isin ATXMPLF03032 \endif
\if :{?as_of} \else \set as_of '2025-11-06 08:00' \endif

\echo 'Official NAV, as known today'
SELECT p.nav_date, p.nav_price, p.currency, d.unique_document_id AS delivered_by
FROM price p
JOIN share_class s ON s.share_class_id = p.share_class_id
JOIN delivery d    ON d.delivery_id = p.delivery_id
WHERE s.isin = :'isin' AND p.nature = 'OFFICIAL' AND p.nav_date > '2025-10-31'
  AND p.replaced_by_delivery_id IS NULL
ORDER BY p.nav_date;

\echo 'Official NAV, as known at' :'as_of'
SELECT p.nav_date, p.nav_price, p.currency, d.unique_document_id AS delivered_by,
       r.unique_document_id AS later_replaced_by
FROM price p
JOIN share_class s   ON s.share_class_id = p.share_class_id
JOIN delivery d      ON d.delivery_id = p.delivery_id
LEFT JOIN delivery r ON r.delivery_id = p.replaced_by_delivery_id
WHERE s.isin = :'isin' AND p.nature = 'OFFICIAL' AND p.nav_date > '2025-10-31'
  AND d.generated_at <= :'as_of'::timestamptz                        -- already delivered then
  AND (r.delivery_id IS NULL OR r.generated_at > :'as_of'::timestamptz) -- and not yet replaced
ORDER BY p.nav_date;
