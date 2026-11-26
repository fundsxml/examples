-- FundsXML end-to-end example, part 2: master data with our own keys.
-- Master data is updated by the latest delivery (latest wins); everything that changes over
-- time and is reported per date lives in the time-series tables (03-06).

CREATE TABLE fund (
    fund_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lei              text UNIQUE,                      -- natural key used to recognise the fund again
    name             text NOT NULL,                    -- Names/OfficialName
    currency         char(3) NOT NULL,
    parent_fund_id   bigint REFERENCES fund,           -- the umbrella of a subfund; NULL otherwise
    single_fund_flag boolean                           -- NULL for subfunds (the flag sits on the umbrella)
);
COMMENT ON TABLE fund IS 'Funds, umbrellas and subfunds in one table: parent_fund_id models Fund/Subfunds/Subfund.';

CREATE TABLE fund_name (                               -- Names: several kinds, several languages
    fund_id  bigint NOT NULL REFERENCES fund,
    kind     text NOT NULL,                            -- OfficialName, ShortName, LanguageName
    language text NOT NULL DEFAULT '',                 -- '' = no language given
    name     text NOT NULL,
    PRIMARY KEY (fund_id, kind, language)
);

CREATE TABLE fund_identifier (                         -- Identifiers: LEI, ISIN, national codes, ...
    fund_id bigint NOT NULL REFERENCES fund,
    scheme  text NOT NULL,
    value   text NOT NULL,
    PRIMARY KEY (fund_id, scheme),
    UNIQUE (scheme, value)
);

CREATE TABLE fund_static (                             -- FundStaticData: changes rarely, but changes
    fund_id                 bigint NOT NULL REFERENCES fund,
    domicile_country        char(2),
    legal_structure         text,                      -- ListedLegalStructure: UCITS, AIF, ...
    inception_date          date,
    open_closed             text,
    sfdr_product_type       text,                      -- SFDRProductType: 6, 8, 9
    ongoing_charges_pct     numeric,                   -- OngoingCosts/OngoingCost[CostType='Ongoing Charges']
    details                 xml NOT NULL,              -- the whole block, for everything not in columns
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
CREATE UNIQUE INDEX fund_static_current ON fund_static (fund_id) WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE share_class (
    share_class_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fund_id        bigint NOT NULL REFERENCES fund,
    isin           char(12) NOT NULL UNIQUE,
    name           text NOT NULL,
    currency       char(3) NOT NULL,
    type_code      text,                               -- ShareClassType/Code
    earning_use    char(1),                            -- R = reinvest, D = distribute
    hedged         boolean
);
COMMENT ON TABLE share_class IS 'Share classes of a fund or subfund, recognised by ISIN.';

CREATE TABLE asset (
    asset_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text NOT NULL,
    asset_type text NOT NULL,                          -- AssetType code: EQ, BO, SC, OP, FU, FX, AC, ...
    currency   char(3) NOT NULL,
    country    char(2),
    details    xml                                     -- AssetDetails as delivered (option, future, bond terms, ...)
);
COMMENT ON TABLE asset IS 'Securities and other instruments, with our own key. Found again via asset_identifier.';
COMMENT ON COLUMN asset.details IS 'The instrument-specific AssetDetails block, kept as XML instead of shredded: '
    'dozens of instrument types with their own fields, read as a whole and written back unchanged by the export.';

CREATE TABLE asset_identifier (
    asset_id bigint NOT NULL REFERENCES asset,
    scheme   text NOT NULL,                            -- ISIN, WKN, SEDOL, CUSIP, SUPPLIER (supplier/type/file id)
    value    text NOT NULL,
    PRIMARY KEY (asset_id, scheme),
    UNIQUE (scheme, value)
);
COMMENT ON TABLE asset_identifier IS 'All known identifiers of an asset. UNIQUE(scheme, value) makes every identifier point to one asset.';
