-- Deliveries overview: who sent what for which date, how far it got, and who released it.
SELECT d.delivery_id AS id, d.unique_document_id, d.data_operation AS op, d.related_document_id AS related,
       d.content_date, d.status, d.released_by,
       (SELECT count(*) FROM delivery_finding f WHERE f.delivery_id = d.delivery_id) AS findings
FROM delivery d
ORDER BY d.delivery_id;
