-- Reconciliation of every current portfolio: positions vs. total net assets, weights vs. 100 %.
-- Ends with an error (psql -v ON_ERROR_STOP=1) if any portfolio does not reconcile.
SELECT fund, nav_date, positions, sum_positions, total_net_assets, currency, sum_weights, ok
FROM portfolio_reconciliation
ORDER BY fund;

SELECT count(*) FILTER (WHERE NOT ok) AS failed, count(*) AS portfolios
FROM portfolio_reconciliation \gset
\if :failed
  \echo 'reconciliation FAILED for' :failed 'of' :portfolios 'portfolios'
  SELECT 1/0 AS reconciliation_failed;
\else
  \echo 'reconciliation ok:' :portfolios 'portfolios'
\endif
