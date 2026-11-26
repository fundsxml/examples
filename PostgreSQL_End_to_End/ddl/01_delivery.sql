-- FundsXML end-to-end example, part 1: deliveries, findings, code lists.
--
-- Layers:  raw      delivery.raw            the file as received, unchanged
--          staging  position_staging        rows waiting for their assets (see 03)
--          core     fund ... document       checked data, our own keys, history
--          reporting views (07)             what users and reports read
--
-- Versioning rule for the whole model: rows are never updated in place. A newer delivery for
-- the same key, or an AMEND/DELETE of the original document, sets replaced_by_delivery_id.
-- "Current" = replaced_by_delivery_id IS NULL; the history stays queryable.

CREATE TABLE delivery (
    delivery_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unique_document_id  text NOT NULL UNIQUE,          -- ControlData/UniqueDocumentID: our idempotency key
    data_supplier       text NOT NULL,                 -- ControlData/DataSupplier/Short
    content_date        date NOT NULL,                 -- the day the data is valid for
    generated_at        timestamptz NOT NULL,          -- ControlData/DocumentGenerated: when the sender wrote it
    schema_version      text,                          -- ControlData/Version
    data_operation      text NOT NULL DEFAULT 'INITIAL' CHECK (data_operation IN ('INITIAL', 'AMEND', 'DELETE')),
    related_document_id text,                          -- the document an AMEND/DELETE refers to
    status              text NOT NULL DEFAULT 'loaded' CHECK (status IN ('loaded', 'checked', 'released')),
    released_by         text,
    released_at         timestamptz,
    file_name           text NOT NULL,
    file_sha256         text NOT NULL,
    received_at         timestamptz NOT NULL DEFAULT now(),
    raw                 xml NOT NULL                   -- the original file, for audit and re-processing
);
COMMENT ON TABLE delivery IS 'Raw layer: one row per received FundsXML file. unique_document_id makes loading idempotent.';

CREATE TABLE delivery_finding (
    delivery_id bigint NOT NULL REFERENCES delivery ON DELETE CASCADE,
    severity    text NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    rule        text NOT NULL,                         -- e.g. RECONCILE_WEIGHTS, UNKNOWN_CODE, NEW_ASSET
    path        text,                                  -- where in the file
    value       text,                                  -- what was found
    message     text NOT NULL
);
COMMENT ON TABLE delivery_finding IS 'Quality stored with the data: warnings and errors of the checks, per delivery.';
CREATE INDEX delivery_finding_delivery ON delivery_finding (delivery_id);

-- Code lists, filled from the enumerations of the schema (ddl/codes_from_xsd.py writes 09_codes.sql).
CREATE TABLE code_list (
    list           text NOT NULL,                      -- the element: PriceNature, AssetType, ...
    code           text NOT NULL,
    schema_version text NOT NULL,                      -- the FundsXML version the code comes from
    PRIMARY KEY (list, code, schema_version)
);
COMMENT ON TABLE code_list IS 'Listed codes per schema version; the loader checks incoming codes against it.';
