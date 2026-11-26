-- Row-level security: a reader sees only the portfolios of its own client's funds.
SELECT client, f.name AS fund FROM client_fund JOIN fund f USING (fund_id);
SET ROLE fundsxml_reader;
SET fundsxml.client = 'INSURER-A';
SELECT fund, nav_date, count(*) AS positions FROM current_position GROUP BY fund, nav_date;
RESET fundsxml.client;
SELECT count(*) AS positions_without_client FROM current_position;
RESET ROLE;
