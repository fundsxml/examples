#!/bin/sh
# The whole chain, end to end, as CI runs it:
#   create the database -> load the deliveries through a landing folder (bad files rejected)
#   -> load again (all skipped) -> correction and deletion -> reconcile -> queries
#   -> generate FundsXML for three partners -> validate -> compare with the golden files
#   -> load one export again (round trip)
#
# Needs: PostgreSQL (PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE and DATABASE_URL), psql, Python with
# requirements.txt, Java 17+ for the XSD 1.1 validation, and FUNDSXML_XSD = the 4.2.9 schema.
#   UPDATE_GOLDEN=1 ./run_all.sh   writes the exports to data/expected/ instead of comparing
set -eu
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
: "${FUNDSXML_XSD:?set FUNDSXML_XSD to the FundsXML 4.2.9 schema (FundsXML.xsd)}"
PSQL="psql -X -q -v ON_ERROR_STOP=1"
export PGOPTIONS="${PGOPTIONS:-} -c client_min_messages=warning"
step() { printf '\n=== %s\n' "$*"; }

step "1. database: ddl/*.sql"
$PSQL -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
for f in ddl/*.sql; do $PSQL -f "$f"; done

step "2. load through a landing folder: good files loaded, bad files rejected with a report"
rm -rf ./out && mkdir -p out/landing
cp data/in/*.xml data/bad/*.xml out/landing/
if $PY loader/load.py --landing --release-by "data team" out/landing; then
  echo "expected the bad files to be rejected"; exit 1
fi
test "$(ls out/landing/done | wc -l)" -eq 7        # 6 deliveries + the duplicate (skipped)
test "$(ls out/landing/error/*.xml | wc -l)" -eq 3
grep -q "Rule:        INCOMPLETE" out/landing/error/cut-off.xml.report.txt
grep -q "Rule:        SCHEMA" out/landing/error/wrong-order.xml.report.txt
grep -q "Rule:        UNKNOWN_SENDER" out/landing/error/unknown-sender.xml.report.txt
cat out/landing/error/wrong-order.xml.report.txt

step "3. load the same files again: every one is skipped"
$PY loader/load.py --xsd "$FUNDSXML_XSD" data/in 2>&1 | tee out/second-run.log
test "$(grep -c 'skipped:' out/second-run.log)" -eq 6

step "4. queries"
$PSQL -c "INSERT INTO client_fund SELECT 'INSURER-A', fund_id FROM fund WHERE name LIKE '%Multi Asset%'"
for q in queries/*.sql; do echo "--- $q"; $PSQL -f "$q"; done

step "5. generate FundsXML for every partner in generator/partners.json, validate, compare"
mkdir -p out/export
$PY generator/export.py --all --date 2025-11-05 --generated 2025-11-06T07:00:00 --out out/export
$PY generator/export.py --partner DATAVENDOR-C --date 2025-11-05 --generated 2025-11-06T10:30:00 \
    --amend EXAMPLE-AM-DATAVENDOR-C-2025-11-05 --out out/export
sh tools/xsd11/validate.sh "$FUNDSXML_XSD" out/export/*.xml
if [ "${UPDATE_GOLDEN:-}" = 1 ]; then
  rm -f data/expected/*.xml && cp out/export/*.xml data/expected/ && echo "golden files updated"
else
  for f in data/expected/*.xml; do cmp "$f" "out/export/$(basename "$f")"; done
  test "$(ls out/export | wc -l)" -eq "$(ls data/expected | wc -l)"
  echo "exports equal the golden files"
fi

step "6. round trip: the export loads again; every asset is found again by its identifiers"
$PY loader/load.py out/export/EXAMPLE-AM-DATAVENDOR-C-2025-11-05.xml 2>&1 | tee out/roundtrip.log
grep -q "status     checked" out/roundtrip.log
if grep -q "new assets" out/roundtrip.log; then echo "the round trip created new assets"; exit 1; fi
$PSQL -f queries/09_reconciliation.sql

echo
echo "all steps passed"
