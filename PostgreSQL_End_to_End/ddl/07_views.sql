-- FundsXML end-to-end example, part 7: the reporting layer.
-- Users read these views, not the tables: the views hide deliveries and replaced rows, and they
-- only show released data. security_invoker: the row-level security of 08_access.sql applies.

CREATE VIEW current_price WITH (security_invoker = true) AS
SELECT f.name AS fund, s.isin, s.name AS share_class, p.nav_date, p.nature, p.nav_price, p.currency,
       d.unique_document_id AS delivered_by
FROM price p
JOIN share_class s ON s.share_class_id = p.share_class_id
JOIN fund f        ON f.fund_id = s.fund_id
JOIN delivery d    ON d.delivery_id = p.delivery_id
WHERE p.replaced_by_delivery_id IS NULL AND d.status = 'released';

CREATE VIEW current_nav WITH (security_invoker = true) AS
SELECT f.name AS fund, s.isin, n.nav_date, n.nature, n.amount, n.currency, n.is_fund_ccy, n.is_share_class_ccy,
       n.shares_outstanding, d.unique_document_id AS delivered_by
FROM nav n
JOIN fund f             ON f.fund_id = n.fund_id
LEFT JOIN share_class s ON s.share_class_id = n.share_class_id
JOIN delivery d         ON d.delivery_id = n.delivery_id
WHERE n.replaced_by_delivery_id IS NULL AND d.status = 'released';

CREATE VIEW latest_portfolio WITH (security_invoker = true) AS
SELECT DISTINCT ON (p.fund_id) p.portfolio_id, p.fund_id, f.name AS fund, p.nav_date, d.unique_document_id AS delivered_by
FROM portfolio p
JOIN fund f     ON f.fund_id = p.fund_id
JOIN delivery d ON d.delivery_id = p.delivery_id
WHERE p.replaced_by_delivery_id IS NULL AND d.status = 'released'
ORDER BY p.fund_id, p.nav_date DESC;

CREATE VIEW current_position WITH (security_invoker = true) AS
SELECT lp.fund, lp.nav_date, pos.look_through, a.name AS asset, a.asset_type, isin.value AS isin,
       pos.position_type, pos.quantity, pos.total_value, pos.currency, pos.percentage
FROM latest_portfolio lp
JOIN position pos ON pos.portfolio_id = lp.portfolio_id
JOIN asset a      ON a.asset_id = pos.asset_id
LEFT JOIN asset_identifier isin ON isin.asset_id = a.asset_id AND isin.scheme = 'ISIN';

-- Documents valid on a given day: current, released, not yet expired.
CREATE FUNCTION documents_in_force(on_day date DEFAULT current_date)
RETURNS TABLE (doc_type text, language text, file_name text, linked boolean, size_bytes bigint, applies_to text)
LANGUAGE sql STABLE AS $$
    SELECT doc.doc_type, doc.language, doc.file_name, doc.url IS NOT NULL, doc.size_bytes,
           string_agg(coalesce(s.isin, f.lei), ', ' ORDER BY coalesce(s.isin, f.lei))
    FROM document doc
    JOIN delivery d              ON d.delivery_id = doc.delivery_id
    JOIN document_target t       ON t.document_id = doc.document_id
    LEFT JOIN share_class s      ON s.share_class_id = t.share_class_id
    LEFT JOIN fund f             ON f.fund_id = t.fund_id
    WHERE doc.replaced_by_delivery_id IS NULL AND d.status = 'released'
      AND (doc.creation_date IS NULL OR doc.creation_date <= on_day)
      AND (doc.expiration_date IS NULL OR doc.expiration_date >= on_day)
    GROUP BY doc.document_id
$$;

-- Reconciliation: positions must add up to the fund's net assets, weights to 100 %.
-- Look-through positions are a breakdown of target funds and are not counted.
CREATE VIEW portfolio_reconciliation AS
SELECT p.portfolio_id, p.delivery_id, f.name AS fund, p.nav_date, f.currency,
       sum(pos.total_value) FILTER (WHERE pos.currency = f.currency) AS sum_positions,
       n.amount                                                      AS total_net_assets,
       sum(pos.percentage)                                           AS sum_weights,
       count(*)                                                      AS positions,
       coalesce(abs(sum(pos.total_value) FILTER (WHERE pos.currency = f.currency) - n.amount) <= 1.00
                AND abs(sum(pos.percentage) - 100) <= 0.05, false)   AS ok  -- tolerance: rounding per position
FROM portfolio p
JOIN fund f       ON f.fund_id = p.fund_id
JOIN position pos ON pos.portfolio_id = p.portfolio_id AND NOT pos.look_through
LEFT JOIN nav n   ON n.fund_id = p.fund_id AND n.share_class_id IS NULL AND n.nav_date = p.nav_date
                 AND n.nature = 'OFFICIAL' AND n.currency = f.currency AND n.replaced_by_delivery_id IS NULL
WHERE p.replaced_by_delivery_id IS NULL
GROUP BY p.portfolio_id, p.delivery_id, f.name, p.nav_date, f.currency, n.amount;
COMMENT ON VIEW portfolio_reconciliation IS 'Sum of positions vs. total net assets and sum of weights, per current portfolio.';

-- Release: only a checked delivery can be released; who and when is recorded.
CREATE FUNCTION release_delivery(doc_id text, by_whom text) RETURNS text LANGUAGE plpgsql AS $$
DECLARE s text;
BEGIN
    UPDATE delivery SET status = 'released', released_by = by_whom, released_at = now()
    WHERE unique_document_id = doc_id AND status = 'checked'
    RETURNING status INTO s;
    IF s IS NULL THEN
        RAISE EXCEPTION 'delivery % is unknown or not checked', doc_id;
    END IF;
    RETURN s;
END $$;
