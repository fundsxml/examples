-- FundsXML end-to-end example, part 6: regulatory templates (RegulatoryReportings).
-- One row per template record (an EMT or EET per share class, a TPT per portfolio), the record
-- as XML, plus the few fields we report on as columns. One table for all templates and
-- versions, but never one column per template field: those change with every template version.

CREATE TABLE regulatory_report (
    report_id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    template                text NOT NULL,             -- EMT, EET, TPT
    template_version        text NOT NULL,             -- e.g. V4.2, V1.1.3, V7
    isin                    text NOT NULL,             -- the instrument (share class) or portfolio reported on
    share_class_id          bigint REFERENCES share_class,
    reference_date          date,
    -- key fields, NULL where a template does not have them
    ongoing_costs           numeric,                   -- EMT: ex-ante ongoing costs, a fraction (0.0158 = 1.58 %)
    sfdr_product_type       text,                      -- EET: Article 6 / 8 / 9
    considers_pai           boolean,                   -- EET: principal adverse impacts considered
    tpt_positions           int,                       -- TPT: number of position records
    content                 xml NOT NULL,              -- the whole template record
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery
);
COMMENT ON TABLE regulatory_report IS 'Regulatory template records: XML plus key fields, one table for all templates and versions.';
CREATE UNIQUE INDEX regulatory_report_current ON regulatory_report (template, template_version, isin)
    WHERE replaced_by_delivery_id IS NULL;
