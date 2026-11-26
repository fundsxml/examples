-- Documents in force on a day: linked or embedded, and what they belong to.
SELECT * FROM documents_in_force('2025-11-05') ORDER BY doc_type, language, file_name;

\echo 'Embedded documents: stored decoded, with their hash'
SELECT file_name, size_bytes, octet_length(content) AS stored_bytes, left(sha256, 16) AS sha256
FROM document WHERE content IS NOT NULL AND replaced_by_delivery_id IS NULL ORDER BY file_name;
