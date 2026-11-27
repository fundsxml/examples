-- What a load left in the database: rows per table (replaced rows included: nothing is overwritten).
SELECT t AS table_name, n AS rows
FROM (VALUES ('delivery',          (SELECT count(*) FROM delivery)),
             ('fund',              (SELECT count(*) FROM fund)),
             ('share_class',       (SELECT count(*) FROM share_class)),
             ('nav',               (SELECT count(*) FROM nav)),
             ('price',             (SELECT count(*) FROM price)),
             ('portfolio',         (SELECT count(*) FROM portfolio)),
             ('position',          (SELECT count(*) FROM position)),
             ('asset',             (SELECT count(*) FROM asset)),
             ('trade',             (SELECT count(*) FROM trade)),
             ('document',          (SELECT count(*) FROM document)),
             ('regulatory_report', (SELECT count(*) FROM regulatory_report))) AS v (t, n);
