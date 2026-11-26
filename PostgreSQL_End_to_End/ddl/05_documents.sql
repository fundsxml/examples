-- FundsXML end-to-end example, part 5: documents (Documents/Document), linked or embedded.

CREATE TABLE document (
    document_id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_type                text NOT NULL,             -- Type/ListedType: Prospectus, PRIIPS-KID, Factsheet, ...
    version                 text,
    language                text NOT NULL,
    name                    text,
    file_name               text NOT NULL,             -- the key: a new delivery of the same file replaces the old one
    format                  text NOT NULL,             -- MIME type
    for_public_usage        boolean,
    creation_date           date,
    expiration_date         date,
    size_bytes              bigint,
    url                     text,                      -- DocumentURL: linked
    content                 bytea,                     -- BinaryData: embedded, decoded
    sha256                  text,                      -- of content, to find the same file again
    delivery_id             bigint NOT NULL REFERENCES delivery,
    replaced_by_delivery_id bigint REFERENCES delivery,
    CHECK (url IS NOT NULL OR content IS NOT NULL)
);
COMMENT ON TABLE document IS 'Fund documents: a link (url) or the file itself (content), with the funds and share classes they belong to.';
CREATE UNIQUE INDEX document_current ON document (file_name) WHERE replaced_by_delivery_id IS NULL;

CREATE TABLE document_target (                         -- Document/Fund, /Subfunds, /ShareClasses: one or many
    document_id    bigint NOT NULL REFERENCES document,
    fund_id        bigint REFERENCES fund,
    share_class_id bigint REFERENCES share_class,
    CHECK ((fund_id IS NULL) <> (share_class_id IS NULL))
);
CREATE INDEX document_target_document ON document_target (document_id);
