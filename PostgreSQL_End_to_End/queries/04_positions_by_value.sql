-- Current positions of one fund, largest first (the reporting view hides deliveries and history).
--   psql -v fund='Multi Asset' -f queries/04_positions_by_value.sql
\if :{?fund} \else \set fund 'Multi Asset' \endif
SELECT asset, asset_type, coalesce(isin, '-') AS isin, position_type, quantity, total_value, currency,
       percentage AS "weight %"
FROM current_position
WHERE fund ILIKE '%' || :'fund' || '%' AND NOT look_through
ORDER BY total_value DESC
LIMIT 8;
