#!/usr/bin/env bash

set -eo pipefail

mkdir -p output/logs

command -v s-put >/dev/null 2>&1 || { echo >&2 "s-put is not available, aborting"; exit 1; }
command -v rapper >/dev/null 2>&1 || { echo >&2 "rapper is not available, aborting"; exit 1; }

export WARSA_ENDPOINT_URL=${WARSA_ENDPOINT_URL:-http://localhost:3030/warsa}
export ARPA_URL=${ARPA_URL:-http://demo.seco.tkk.fi/arpa}
export LOG_LEVEL="DEBUG"

./convert.sh $1

echo "Updating camps and hospitals to Fuseki"
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/camps_combined.ttl

curl -f --data-urlencode "query=$(cat sparql/construct_camps.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/camps.ttl


#echo "Converting sources to ttl"
#python src/csv_to_rdf.py SOURCES output/hospitals_cropped.csv --outdata=output/hospitals_raw.ttl
#

echo "Linking ranks"

python src/linker.py ranks output/prisoners_plain.ttl output/rank_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" \
    --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking units"

cat output/prisoners_plain.ttl output/rank_links.ttl > output/prisoners_temp.ttl

# Updated data needed for unit linking
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_temp.ttl

curl -f --data-urlencode "query=$(cat sparql/period.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/periods.ttl

./link_units.sh

echo "Linking occupations"

python src/linker.py occupations output/prisoners_plain.ttl output/occupation_links.ttl \
    --endpoint "$WARSA_ENDPOINT_URL/sparql" --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking municipalities"

python src/linker.py municipalities output/prisoners_plain.ttl output/municipality_links.ttl \
    --endpoint "$WARSA_ENDPOINT_URL/sparql" --arpa $ARPA_URL/pnr_municipality --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking people"

echo "Adding manual links"

cat output/prisoners_plain.ttl output/rank_links.ttl output/unit_linked_validated.ttl \
    output/occupation_links.ttl output/municipality_links.ttl input_rdf/additional_links.ttl > output/prisoners_temp.ttl
python src/linker.py persons output/prisoners_temp.ttl output/persons_linked.ttl \
    --endpoint "$WARSA_ENDPOINT_URL/sparql" --logfile output/logs/linker.log --loglevel $LOG_LEVEL
rm output/prisoners_temp.ttl

sed -r 's/^(p:.*) cidoc:P70_documents (<.*>)/\2 cidoc:P70i_is_documented_in \1/' output/persons_linked.ttl > output/person_backlinks.ttl

echo "Linking camps and hospitals"
cat output/prisoners_plain.ttl output/camps.ttl > output/prisoners_temp_2.ttl
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_temp_2.ttl

python src/linker.py camps output/prisoners_plain.ttl output/camp_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" \
    --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Consolidating prisoners"

cat output/prisoners_plain.ttl output/rank_links.ttl output/unit_linked_validated.ttl output/persons_linked.ttl \
    output/occupation_links.ttl output/camp_links.ttl output/municipality_links.ttl input_rdf/additional_links.ttl > output/prisoners_full.ttl
rapper -i turtle output/prisoners_full.ttl -o turtle > output/prisoners_.ttl
rm output/prisoners_full.ttl

echo "Generating people..."

echo "...Updating db with prisoners"
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_.ttl

echo "...Constructing people"
curl -f --data-urlencode "query=$(cat sparql/construct_people.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/prisoner_people.ttl

echo "...Constructing documents links"
curl -f --data-urlencode "query=$(cat sparql/construct_documents_links.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/prisoner_documents_links.ttl

echo "...Updating db with new people"
cat output/prisoner_people.ttl output/prisoner_documents_links.ttl > prisoners_temp.ttl
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoner_persons output/prisoner_people.ttl
rm prisoners_temp.ttl

for construct in births promotions unit_joinings captures disappearances
do
    echo "...Constructing $construct"
curl -f --data-urlencode "query=$(cat sparql/construct_$construct.sparql)" $WARSA_ENDPOINT_URL/sparql -v > "output/prisoner_$construct.ttl"
done

echo "...Deleting temp graph"
s-delete $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoner_persons

echo "Finishing prisoners"

cat output/prisoners_.ttl output/prisoner_documents_links.ttl > output/prisoners_full.ttl
rapper -i turtle output/prisoners_full.ttl -o turtle > output/prisoners.ttl
rm output/prisoners_full.ttl

echo "...Finished"
