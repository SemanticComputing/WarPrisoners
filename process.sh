#!/bin/sh

mkdir -p output/logs

command -v s-put >/dev/null 2>&1 || { echo >&2 "s-put is not available, aborting"; exit 1; }
command -v rapper >/dev/null 2>&1 || { echo >&2 "rapper is not available, aborting"; exit 1; }

export WARSA_ENDPOINT_URL=${WARSA_ENDPOINT_URL:-http://localhost:3030/warsa}
export ARPA_URL=${ARPA_URL:-http://demo.seco.tkk.fi/arpa}

echo "Converting to csv" &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/prisoners.xls --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/camps.xlsx --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/hospitals.xlsx --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/sources.xlsx --outdir data &&

# Remove dummy rows from beginning and end of CSVs
# TODO: Remove the end-of-file content in a less error prone way using Python (e.g. pruning the resources)
tail -n +4 data/camps.csv | head -n -4 > output/camps_cropped.csv
head -n -2 data/hospitals.csv > output/hospitals_cropped.csv
tail -n +2 data/sources.csv > output/sources_cropped.csv

echo "Converting camps and hospitals to ttl" &&
python src/csv_to_rdf.py CAMPS output/camps_cropped.csv --outdata=output/camps_raw.ttl --outschema=output/camp_schema.ttl &&
python src/csv_to_rdf.py HOSPITALS output/hospitals_cropped.csv --outdata=output/hospitals_raw.ttl &&

# Fix resource URIs
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/camp_/g' output/camps_raw.ttl &&
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/hospital_/g' output/hospitals_raw.ttl &&

# Combine camps and hospitals
cat output/camps_raw.ttl output/hospitals_raw.ttl > output/camps_combined.ttl &&

# TODO: Transform this all to Python mapping

## Fix property URIs
sed -r -i 's/:sijainti /:location /g' output/camps_combined.ttl &&

sed -r -i 's/:vankeuspaikannnumero /:camp_id /g' output/camps_combined.ttl &&
sed -r -i 's/:vankeuspaikka /:captivity_location /g' output/camps_combined.ttl &&
sed -r -i 's/:toiminta-aika /:time_of_operation /g' output/camps_combined.ttl &&
sed -r -i 's/:tietoa-vankeuspaikasta /:camp_information /g' output/camps_combined.ttl &&
sed -r -i 's/:valokuvat /:camp_photographs /g' output/camps_combined.ttl &&
sed -r -i 's/:koordinaatit\-kartalla /:coordinates /g' output/camps_combined.ttl &&

sed -r -i 's/:sairaala /:camp_id /g' output/camps_combined.ttl &&
sed -r -i 's/:sairaalan\-tyyppi /:hospital_type /g' output/camps_combined.ttl &&
sed -r -i 's/:tietoa-sairaalasta /:camp_information /g' output/camps_combined.ttl &&
sed -r -i 's/:kuvat /:camp_photographs /g' output/camps_combined.ttl &&
sed -r -i 's/:koordinaatit\-kartalla /:coordinates /g' output/camps_combined.ttl &&

echo "Updating camps and hospitals to Fuseki" &&
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/camps_combined.ttl &&

curl -f --data-urlencode "query=$(cat sparql/construct_camps.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/camps.ttl &&

python src/csv_to_rdf.py PRISONERS data/prisoners.csv --outdata=output/prisoners_plain.ttl --outschema=output/schema.ttl &&

cat input_rdf/schema_base.ttl output/schema.ttl > output/schema_full.ttl &&
rapper -i turtle output/schema_full.ttl -o turtle > output/prisoners_schema.ttl &&
rm output/schema_full.ttl &&

echo "Linking ranks" &&

python src/linker.py ranks output/prisoners_plain.ttl output/rank_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" &&

echo "Linking units" &&

cat output/prisoners_plain.ttl output/rank_links.ttl > output/prisoners_temp.ttl &&

# Updated data needed for unit linking
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_temp.ttl &&

curl -f --data-urlencode "query=$(cat sparql/period.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/periods.ttl &&

./link_units.sh &&

echo "Linking occupations" &&

python src/linker.py occupations output/prisoners_plain.ttl output/occupation_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" &&

echo "Linking people" &&

cat output/prisoners_plain.ttl output/rank_links.ttl output/unit_linked_validated.ttl output/occupation_links.ttl > output/prisoners_temp.ttl &&
python src/linker.py persons output/prisoners_temp.ttl output/persons_linked.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" &&
rm output/prisoners_temp.ttl &&

sed -r 's/^(p:.*) cidoc:P70_documents (<.*>)/\2 cidoc:P70i_is_documented_in \1/' output/persons_linked.ttl > output/person_backlinks.ttl &&

echo "Linking camps and hospitals" &&
cat output/prisoners_plain.ttl output/camps.ttl > output/prisoners_temp_2.ttl &&
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_temp_2.ttl &&

python src/linker.py camps output/prisoners_plain.ttl output/camp_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" &&

# TODO: Link places using Arpa-linker

echo "Consolidating prisoners" &&

cat output/prisoners_plain.ttl output/rank_links.ttl output/unit_linked_validated.ttl output/persons_linked.ttl output/occupation_links.ttl output/camp_links.ttl > output/prisoners_full.ttl &&
rapper -i turtle output/prisoners_full.ttl -o turtle > output/prisoners.ttl &&
rm output/prisoners_full.ttl &&

echo "Generating people..." &&

echo "...Updating db with prisoners" &&
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners.ttl &&

echo "...Constructing people" &&
curl -f --data-urlencode "query=$(cat sparql/construct_people.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/prisoner_people.ttl &&

echo "...Constructing documents links" &&
curl -f --data-urlencode "query=$(cat sparql/construct_documents_links.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/prisoner_documents_links.ttl &&

echo "...Updating db with new people" &&
cat output/prisoner_people.ttl output/prisoner_documents_links.ttl > prisoners_temp.ttl &&
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoner_persons output/prisoner_people.ttl &&
rm prisoners_temp.ttl &&

for construct in births promotions ranks unit_joinings captures disappearances
do
    echo "...Constructing $construct" &&
curl -f --data-urlencode "query=$(cat sparql/construct_$construct.sparql)" $WARSA_ENDPOINT_URL/sparql -v > "output/prisoner_$construct.ttl"
done &&

echo "...Deleting temp graph" &&
s-delete $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoner_persons &&

echo "Finishing prisoners" &&

cat output/prisoners.ttl output/prisoner_documents_links.ttl > output/prisoners_full.ttl &&
rapper -i turtle output/prisoners_full.ttl -o turtle > output/prisoners.ttl &&
rm output/prisoners_full.ttl &&

echo "...Finished"
