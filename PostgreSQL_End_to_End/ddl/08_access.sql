-- FundsXML end-to-end example, part 8: access.
-- Separate roles for loading, releasing and reading. Readers see only the funds of their client:
-- row-level security on portfolio and position, with the client set per session:
--     SET ROLE fundsxml_reader; SET fundsxml.client = 'INSURER-A';
-- The tables' owner (the loader in this example) is not subject to these policies.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fundsxml_reader') THEN
        CREATE ROLE fundsxml_reader NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fundsxml_releaser') THEN
        CREATE ROLE fundsxml_releaser NOLOGIN;
    END IF;
END $$;

CREATE TABLE client_fund (
    client  text NOT NULL,
    fund_id bigint NOT NULL REFERENCES fund,
    PRIMARY KEY (client, fund_id)
);
COMMENT ON TABLE client_fund IS 'Which client may see which fund''s portfolios.';

ALTER TABLE portfolio ENABLE ROW LEVEL SECURITY;
CREATE POLICY portfolio_of_client ON portfolio FOR SELECT TO fundsxml_reader
    USING (fund_id IN (SELECT fund_id FROM client_fund WHERE client = current_setting('fundsxml.client', true)));

ALTER TABLE position ENABLE ROW LEVEL SECURITY;
CREATE POLICY position_of_client ON position FOR SELECT TO fundsxml_reader
    USING (portfolio_id IN (SELECT portfolio_id FROM portfolio));   -- portfolio is filtered itself

GRANT USAGE ON SCHEMA public TO fundsxml_reader, fundsxml_releaser;
GRANT SELECT ON current_price, current_nav, latest_portfolio, current_position TO fundsxml_reader;
GRANT SELECT ON fund, share_class, price, nav, portfolio, position, asset, asset_identifier, delivery,
                document, document_target, client_fund TO fundsxml_reader;
GRANT EXECUTE ON FUNCTION documents_in_force(date) TO fundsxml_reader;
GRANT SELECT ON delivery, portfolio_reconciliation, delivery_finding TO fundsxml_releaser;
GRANT EXECUTE ON FUNCTION release_delivery(text, text) TO fundsxml_releaser;
GRANT UPDATE (status, released_by, released_at) ON delivery TO fundsxml_releaser;
