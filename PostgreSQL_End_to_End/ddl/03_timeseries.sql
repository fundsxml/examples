-- FundsXML end-to-end example, part 3: prices, net assets, portfolios and positions.
-- Everything here repeats: many dates, several natures per date (ESTIMATED, OFFICIAL),
-- several currencies per amount, many portfolios per fund, many positions per portfolio.

CREATE TABLE price (                                   -- ShareClass/Prices/Price
    price_id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    share_class_id          bigint NOT NULL REFERENCES share_class,
    nav_date                date NOT NULL,
    nature                  text NOT NULL,             -- PriceNature: OFFICIAL / ESTIMATED / TECHNICAL
    nav_price               numeric NOT NULL,
    subscription_price      numeric,
    redemption_price        numeric,
    currency                char(3) NOT NULL,          -- PriceCurrency
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
COMMENT ON TABLE price IS 'NAV per share, one row per share class, date and nature. Versioned: replaced, never overwritten.';
CREATE UNIQUE INDEX price_current ON price (share_class_id, nav_date, nature) WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE nav (                                     -- TotalAssetValues/TotalAssetValue
    nav_id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fund_id                 bigint NOT NULL REFERENCES fund,
    share_class_id          bigint REFERENCES share_class,  -- NULL = fund level
    nav_date                date NOT NULL,
    nature                  text NOT NULL,             -- TotalAssetNature
    amount                  numeric NOT NULL,          -- TotalNetAssetValue/Amount: never without its currency
    currency                char(3) NOT NULL,
    is_fund_ccy             boolean NOT NULL DEFAULT false,
    is_share_class_ccy      boolean NOT NULL DEFAULT false,
    shares_outstanding      numeric,
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
COMMENT ON TABLE nav IS 'Total net assets per fund or share class, date and nature; one row per currency reported.';
CREATE UNIQUE INDEX nav_current ON nav (fund_id, share_class_id, nav_date, nature, currency) NULLS NOT DISTINCT
    WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE portfolio (                               -- FundDynamicData/Portfolios/Portfolio
    portfolio_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fund_id                 bigint NOT NULL REFERENCES fund,
    nav_date                date NOT NULL,
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
COMMENT ON TABLE portfolio IS 'One snapshot of a fund per date and delivery; positions, trades and income hang off it.';
CREATE UNIQUE INDEX portfolio_current ON portfolio (fund_id, nav_date) WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE position (                                -- Positions/Position and PositionsDecomposed/Positions/Position
    portfolio_id  bigint NOT NULL REFERENCES portfolio,
    position_no   int NOT NULL,                        -- order in the file, so the export can keep it
    look_through  boolean NOT NULL DEFAULT false,      -- true = from PositionsDecomposed (target funds' holdings)
    asset_id      bigint NOT NULL REFERENCES asset,
    position_type text NOT NULL,                       -- the Position child element: Equity, Bond, Future, ...
    total_value   numeric NOT NULL,                    -- TotalValue/Amount (fund currency)
    currency      char(3) NOT NULL,
    percentage    numeric,                             -- TotalPercentage
    quantity      numeric,                             -- Units / Nominal / Contracts ...
    details       xml NOT NULL,                        -- the position element, for fields not in columns
    PRIMARY KEY (portfolio_id, look_through, position_no)
);
COMMENT ON TABLE position IS 'Holdings of a portfolio, resolved to our assets. Inherits the version of its portfolio.';
CREATE INDEX position_asset ON position (asset_id);

CREATE UNLOGGED TABLE position_staging (
    delivery_id    bigint NOT NULL,
    portfolio_id   bigint NOT NULL,
    position_no    int NOT NULL,
    look_through   boolean NOT NULL,
    file_unique_id text NOT NULL,                      -- Position/UniqueID: only valid inside this one file
    position_type  text NOT NULL,
    total_value    numeric NOT NULL,
    currency       char(3) NOT NULL,
    percentage     numeric,
    quantity       numeric,
    details        text NOT NULL
);
COMMENT ON TABLE position_staging IS 'Staging layer: positions arrive before AssetMasterData, so they wait here until the assets are known. Unlogged: throwaway rows.';
