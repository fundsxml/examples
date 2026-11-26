-- FundsXML end-to-end example, part 4: transactions in their four places.
--   share class:  Flows/Flow (subscriptions, redemptions)  -> sc_flow
--                 Distributions/Distribution               -> distribution
--   portfolio:    Transactions/Transaction (the fund's own trades and cash movements) -> trade
--                 Earnings/Earning (dividends, coupons, interest)                     -> earning

CREATE TABLE sc_flow (
    share_class_id          bigint NOT NULL REFERENCES share_class,
    transaction_id          text NOT NULL,             -- TransactionID: the sender's key of the flow
    trade_date              date NOT NULL,
    accounting_date         date NOT NULL,
    settlement_date         date,
    flow_type               text NOT NULL,             -- TransactionType: SUB / RED
    units                   numeric NOT NULL,
    value                   numeric NOT NULL,
    currency                char(3) NOT NULL,
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
CREATE UNIQUE INDEX sc_flow_current ON sc_flow (share_class_id, transaction_id) WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE distribution (
    share_class_id          bigint NOT NULL REFERENCES share_class,
    ex_date                 date NOT NULL,
    status                  text NOT NULL,             -- DividendStatus: announced, estimated or official
    record_date             date,
    payment_date            date,
    gross_per_share         numeric,
    net_per_share           numeric,
    currency                char(3) NOT NULL,
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
CREATE UNIQUE INDEX distribution_current ON distribution (share_class_id, ex_date) WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE trade (
    portfolio_id      bigint NOT NULL REFERENCES portfolio,
    transaction_id    text NOT NULL,
    asset_id          bigint REFERENCES asset,         -- NULL for pure cash movements
    kind              text NOT NULL,                   -- TransactionKind: BUY, SELL, CASH, ...
    entry_date        date NOT NULL,
    valuta_date       date,
    quantity          numeric,                         -- NominalOrUnitsOrContracts
    settlement_amount numeric,
    settlement_ccy    char(3),
    counterparty_lei  text,
    posting_text      text,
    details           xml NOT NULL,                    -- the whole Transaction, for fields not in columns
    PRIMARY KEY (portfolio_id, transaction_id)
);
COMMENT ON TABLE trade IS 'The fund''s own transactions. Inherits the version of its portfolio.';

CREATE TABLE earning (
    portfolio_id bigint NOT NULL REFERENCES portfolio,
    earning_id   text NOT NULL,
    asset_id     bigint REFERENCES asset,
    kind         text NOT NULL,                        -- EarningKind: Dividend, Coupon, Interest, ...
    entry_date   date NOT NULL,
    valuta_date  date,
    value        numeric NOT NULL,                     -- EntryValue in the entry currency
    currency     char(3) NOT NULL,
    posting_text text,
    details      xml NOT NULL,                         -- the whole Earning, for fields not in columns
    PRIMARY KEY (portfolio_id, earning_id)
);
COMMENT ON TABLE earning IS 'Income of the portfolio. Inherits the version of its portfolio.';
