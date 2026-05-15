-- Shared relational model for FundsXML positions data.
--
-- Portable ANSI-ish DDL (works on SQLite/Postgres; see notes for Oracle and
-- SQL Server type tweaks). One row set per source document, keyed by the
-- ControlData/UniqueDocumentID so multiple files can coexist.
--
-- Faithful enough to round-trip the canonical positions sample back to
-- XSD-valid FundsXML (fund + share classes + positions + asset master data).

CREATE TABLE fund (
    document_id     VARCHAR(128) NOT NULL,
    lei             VARCHAR(20),
    official_name   VARCHAR(256) NOT NULL,
    currency        CHAR(3)      NOT NULL,
    content_date    DATE,
    nav_date        DATE,
    total_nav       DECIMAL(20,2) NOT NULL,
    fxml_version    VARCHAR(16),                -- absent for 4.0.0
    PRIMARY KEY (document_id)
);

CREATE TABLE share_class (
    document_id     VARCHAR(128) NOT NULL,
    isin            CHAR(12)     NOT NULL,
    official_name   VARCHAR(256),
    currency        CHAR(3)      NOT NULL,
    nav_price       DECIMAL(20,6),
    nav_fund_ccy    DECIMAL(20,2),              -- NAV in fund currency
    shares_outstanding DECIMAL(28,6),
    PRIMARY KEY (document_id, isin),
    FOREIGN KEY (document_id) REFERENCES fund (document_id)
);

CREATE TABLE asset (
    document_id     VARCHAR(128) NOT NULL,
    unique_id       VARCHAR(256) NOT NULL,
    isin            CHAR(12),
    name            VARCHAR(256),
    asset_type      CHAR(2),                    -- EQ, BO, SC, ...
    currency        CHAR(3),
    country         CHAR(2),
    PRIMARY KEY (document_id, unique_id),
    FOREIGN KEY (document_id) REFERENCES fund (document_id)
);

CREATE TABLE position (
    document_id     VARCHAR(128) NOT NULL,
    unique_id       VARCHAR(256) NOT NULL,      -- joins to asset.unique_id
    isin            CHAR(12),
    currency        CHAR(3),
    value_fund_ccy  DECIMAL(20,2) NOT NULL,
    percentage      DECIMAL(9,4)  NOT NULL,
    kind            VARCHAR(16),                -- Position class element:
                                                -- Equity/Bond/ShareClass/...
    kind_qty        DECIMAL(28,6),              -- its quantity child
                                                -- (Units/Nominal/Shares/Contracts)
    PRIMARY KEY (document_id, unique_id),
    FOREIGN KEY (document_id) REFERENCES fund (document_id)
);

-- Dialect notes
--   Oracle      : VARCHAR(n) -> VARCHAR2(n); DECIMAL -> NUMBER; CHAR ok.
--                 An XMLType staging column is shown in load_from_fundsxml.
--   SQL Server  : VARCHAR ok; DECIMAL ok; use an XML column for staging.
--   Postgres    : as-is; a native `xml` staging column is used for xmltable.
