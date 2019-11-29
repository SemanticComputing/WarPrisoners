#!/usr/bin/env bash

set -eo pipefail

mkdir -p output/logs
mkdir -p output/persons

command -v s-put >/dev/null 2>&1 || { echo >&2 "s-put is not available, aborting"; exit 1; }
command -v rapper >/dev/null 2>&1 || { echo >&2 "rapper is not available, aborting"; exit 1; }

export WARSA_ENDPOINT_URL=${WARSA_ENDPOINT_URL:-http://localhost:3030/warsa}
export ARPA_URL=${ARPA_URL:-http://demo.seco.tkk.fi/arpa}
export LOG_LEVEL="DEBUG"

rm -f output/*.csv
rm -f output/persons/*

./convert.sh $1

echo "Updating camps and hospitals to Fuseki"
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/camps_combined.ttl

curl -f --data-urlencode "query=$(cat sparql/construct_camps.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/camps.ttl

echo "Pseudonymizing people and hiding personal information"

python src/prune_nonpublic.py output/prisoners_plain.ttl output/prisoners_pseudonymized.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql"  \
    --logfile output/logs/person_pruning.log --loglevel $LOG_LEVEL

echo "Linking ranks"

python src/linker.py ranks output/prisoners_pseudonymized.ttl output/rank_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" \
    --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking units"

cat output/prisoners_pseudonymized.ttl output/rank_links.ttl > output/prisoners_temp.ttl

# Updated data needed for unit linking
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_temp.ttl

curl -f --data-urlencode "query=$(cat sparql/period.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/periods.ttl

./link_units.sh

echo "Linking occupations"

python src/linker.py occupations output/prisoners_pseudonymized.ttl output/occupation_links.ttl \
    --endpoint "$WARSA_ENDPOINT_URL/sparql" --logfile output/logs/occupations.log --loglevel $LOG_LEVEL

echo "Linking municipalities"

python src/linker.py municipalities output/prisoners_pseudonymized.ttl output/municipality_links.ttl \
    --endpoint "$WARSA_ENDPOINT_URL/sparql" --arpa $ARPA_URL/pnr_municipality --logfile output/logs/municipalities.log --loglevel $LOG_LEVEL

echo "Linking Sotilaan Ääni magazines"

python src/linker.py sotilaan_aani output/prisoners_pseudonymized.ttl output/sotilaan_aani_links.ttl \
    --output2 output/_media_sotilaan_aani.ttl --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking Person documents"

python src/linker.py person_documents output/prisoners_pseudonymized.ttl output/person_document_links.ttl \
    --output2 output/_media_person_documents.ttl --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking videos"

python src/linker.py videos output/prisoners_pseudonymized.ttl output/person_video_links.ttl \
    --output2 output/_media_videos.ttl --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking people"

cat output/prisoners_pseudonymized.ttl output/rank_links.ttl output/unit_linked_validated.ttl \
    output/occupation_links.ttl output/municipality_links.ttl input_rdf/additional_links.ttl > output/prisoners_temp.ttl
python src/linker.py persons output/prisoners_temp.ttl output/persons_linked.ttl \
    --endpoint "$WARSA_ENDPOINT_URL/sparql" --logfile output/logs/linker.log --loglevel $LOG_LEVEL
rm output/prisoners_temp.ttl

sed -r 's/^(p:.*) cidoc:P70_documents (<.*>)/\2 cidoc:P70i_is_documented_in \1/' output/persons_linked.ttl > output/persons_backlinks.ttl

echo "Linking camps and hospitals"

cat output/prisoners_pseudonymized.ttl output/camps.ttl > output/prisoners_temp.ttl
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_temp.ttl
rm output/prisoners_temp.ttl

python src/linker.py camps output/prisoners_pseudonymized.ttl output/camp_links.ttl --endpoint "$WARSA_ENDPOINT_URL/sparql" \
    --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Linking sources"

python src/linker.py sources output/prisoners_pseudonymized.ttl output/_prisoners_with_sources.ttl \
    --logfile output/logs/linker.log --loglevel $LOG_LEVEL

echo "Consolidating prisoners"

cat output/_prisoners_with_sources.ttl output/rank_links.ttl output/unit_linked_validated.ttl output/persons_linked.ttl \
    output/occupation_links.ttl output/camp_links.ttl output/municipality_links.ttl output/sotilaan_aani_links.ttl \
    output/person_document_links.ttl output/person_video_links.ttl \
    input_rdf/additional_links.ttl > output/prisoners_.ttl

echo "Generating people..."

echo "...Updating db with prisoners"
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoners output/prisoners_.ttl

echo "...Constructing people"
curl -f --data-urlencode "query=$(cat sparql/construct_people.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/persons/_prisoner_persons.ttl
rapper -i turtle output/persons/_prisoner_persons.ttl -o turtle > output/persons/prisoner_persons.ttl

echo "...Constructing documents links"
curl -f --data-urlencode "query=$(cat sparql/construct_documents_links.sparql)" $WARSA_ENDPOINT_URL/sparql -v > output/documents_links.ttl

echo "...Updating db with new people"
cat output/persons/prisoner_persons.ttl output/documents_links.ttl > output/prisoner_people_temp.ttl
s-put $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoner_persons output/prisoner_people_temp.ttl
rm output/prisoner_people_temp.ttl

for construct in births promotions unit_joinings captures disappearances deaths
do
    echo "...Constructing $construct"
    curl -f --data-urlencode "query=$(cat sparql/construct_$construct.sparql)" $WARSA_ENDPOINT_URL/sparql -v > "output/persons/_prisoner_$construct.ttl"
    rapper -i turtle "output/persons/_prisoner_$construct.ttl" -o turtle > "output/persons/prisoner_$construct.ttl"
done
rm output/persons/_prisoner_*

echo "...Deleting temp graph"
s-delete $WARSA_ENDPOINT_URL/data http://ldf.fi/warsa/prisoner_persons

echo "Finishing prisoners"

cat output/_media_sotilaan_aani.ttl output/_media_person_documents.ttl output/_media_videos.ttl > output/_media_full.ttl
rapper -i turtle output/_media_full.ttl -o turtle > output/prisoners_media.ttl

cat output/prisoners_.ttl output/documents_links.ttl > output/prisoners_full.ttl
rapper -i turtle output/prisoners_full.ttl -o turtle > output/prisoners.ttl
rm output/prisoners_.ttl
rm output/prisoners_full.ttl

echo "...Finished"
