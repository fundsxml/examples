-- ===========================================================================
-- Relational model for FundsXML positions data — MULTI-FUND capable.
--
-- A FundsXML document is a tree:
--   FundsXML4
--     ControlData                         -> table `document`  (1 per file)
--     Funds/Fund (1..n)                    -> table `fund`
--       SingleFund/ShareClasses/ShareClass -> table `share_class`
--       FundDynamicData/Portfolios/Portfolio (1..n) -> table `portfolio`
--         Positions/Position (1..n)        -> table `position`
--     AssetMasterData/Asset (1..n)         -> table `asset`  (document-scoped)
--
-- WHY surrogate ordinal keys (*_seq):
--   FundsXML does not guarantee a stable business key for a Fund or Portfolio
--   (LEI is optional and not always unique within a file; a Portfolio has no
--   id at all). To round-trip *exactly* — same number of funds/portfolios,
--   same order, duplicates preserved — we number them by their position in
--   the document (fund_seq, portfolio_seq, position_seq, 1-based). This makes
--   the export deterministic and the import lossless for the captured model.
--
-- WHY `asset` is document-scoped (no fund_seq):
--   AssetMasterData sits directly under FundsXML4, shared by all funds, and
--   Asset/UniqueID is an xs:ID (unique per document). Positions reference it
--   by that UniqueID — exactly the FundsXML Position<->Asset link.
--
-- Portable ANSI-ish DDL: runs as-is on SQLite (used by the runnable examples)
-- and PostgreSQL. For the other engines adjust types:
--   Oracle      : VARCHAR(n)->VARCHAR2(n), DECIMAL->NUMBER, CHAR ok
--   SQL Server  : VARCHAR/DECIMAL ok; CHAR ok
-- (An XML staging column is shown in ../load_from_fundsxml/ for those engines.)
-- ===========================================================================

CREATE TABLE document (
    document_id      VARCHAR(128) NOT NULL,
    generated        VARCHAR(32),                 -- ControlData/DocumentGenerated
    version          VARCHAR(16),                 -- absent for FundsXML 4.0.0
    content_date     DATE,
    data_operation   VARCHAR(16),                 -- INITIAL / DELTA / ...
    supplier_country CHAR(2),
    supplier_short   VARCHAR(64),
    supplier_name    VARCHAR(256),
    supplier_type    VARCHAR(64),
    PRIMARY KEY (document_id)
);

CREATE TABLE fund (
    document_id      VARCHAR(128) NOT NULL,
    fund_seq         INTEGER      NOT NULL,        -- 1-based order within Funds
    lei              VARCHAR(20),
    official_name    VARCHAR(256) NOT NULL,
    currency         CHAR(3)      NOT NULL,
    single_fund_flag VARCHAR(8),
    nav_date         DATE,
    total_nav        DECIMAL(20,2) NOT NULL,
    PRIMARY KEY (document_id, fund_seq),
    FOREIGN KEY (document_id) REFERENCES document (document_id)
);

CREATE TABLE share_class (
    document_id        VARCHAR(128) NOT NULL,
    fund_seq           INTEGER      NOT NULL,
    isin               CHAR(12)     NOT NULL,
    official_name      VARCHAR(256),
    currency           CHAR(3)      NOT NULL,
    nav_price          DECIMAL(20,6),
    nav_fund_ccy       DECIMAL(20,2),              -- NAV in the fund currency
    shares_outstanding DECIMAL(28,6),
    PRIMARY KEY (document_id, fund_seq, isin),
    FOREIGN KEY (document_id, fund_seq) REFERENCES fund (document_id, fund_seq)
);

CREATE TABLE portfolio (
    document_id      VARCHAR(128) NOT NULL,
    fund_seq         INTEGER      NOT NULL,
    portfolio_seq    INTEGER      NOT NULL,        -- 1-based within the fund
    nav_date         DATE,
    PRIMARY KEY (document_id, fund_seq, portfolio_seq),
    FOREIGN KEY (document_id, fund_seq) REFERENCES fund (document_id, fund_seq)
);

CREATE TABLE position (
    document_id      VARCHAR(128) NOT NULL,
    fund_seq         INTEGER      NOT NULL,
    portfolio_seq    INTEGER      NOT NULL,
    position_seq     INTEGER      NOT NULL,        -- 1-based within the portfolio
    unique_id        VARCHAR(256),                 -- joins to asset.unique_id
    isin             CHAR(12),
    currency         CHAR(3),
    value_fund_ccy   DECIMAL(20,2) NOT NULL,       -- TotalValue in fund ccy
    percentage       DECIMAL(9,4)  NOT NULL,       -- TotalPercentage
    kind             VARCHAR(16),                  -- Equity/Bond/ShareClass/...
    kind_qty         DECIMAL(28,6),                -- Units/Nominal/Shares/Contracts
    PRIMARY KEY (document_id, fund_seq, portfolio_seq, position_seq),
    FOREIGN KEY (document_id, fund_seq, portfolio_seq)
        REFERENCES portfolio (document_id, fund_seq, portfolio_seq)
);

CREATE TABLE asset (
    document_id      VARCHAR(128) NOT NULL,
    unique_id        VARCHAR(256) NOT NULL,
    isin             CHAR(12),
    name             VARCHAR(256),
    asset_type       CHAR(2),                      -- EQ, BO, SC, ...
    currency         CHAR(3),
    country          CHAR(2),
    PRIMARY KEY (document_id, unique_id),
    FOREIGN KEY (document_id) REFERENCES document (document_id)
);
