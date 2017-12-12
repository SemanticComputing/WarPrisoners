#!/usr/bin/env bash

mkdir -p output

command -v s-put >/dev/null 2>&1 || { echo >&2 "s-put is not available, aborting"; exit 1; }
command -v rapper >/dev/null 2>&1 || { echo >&2 "rapper is not available, aborting"; exit 1; }

echo "Converting to csv" &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/prisoners.xls --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/camps.xlsx --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/hospitals.xlsx --outdir data &&

echo "Converting to ttl" &&
python csv_to_rdf.py CAMPS data/camps.csv --outdata=output/camps.ttl --outschema=output/camp_schema.ttl &&
python csv_to_rdf.py HOSPITALS data/hospitals.csv --outdata=output/camps2.ttl &&

sed -r -i 's/\/prisoners\/r\_/\/prisoners\/camp_/g' output/camps.ttl &&
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/hospital_/g' output/camps2.ttl &&

cat output/camps.ttl output/camps2.ttl > output/camps.ttl &&
rm output/camps2.ttl &&

python csv_to_rdf.py PRISONERS data/prisoners.csv --outdata=output/prisoners_plain.ttl --outschema=output/schema.ttl &&

echo "Linking ranks" &&

python linker.py ranks output/prisoners_plain.ttl output/rank_links.ttl --endpoint "http://localhost:3030/warsa/sparql" &&

echo "Linking units" &&

cat output/prisoners_plain.ttl output/rank_links.ttl > output/prisoners_temp.ttl &&

# Updated data needed for unit linking
s-put http://localhost:3030/warsa/data http://ldf.fi/warsa/prisoners output/prisoners_temp.ttl &&

echo 'query=' | cat - sparql/period.sparql | sed 's/&/%26/g' | curl -d @- http://localhost:3030/warsa/sparql -v > output/periods.ttl &&

./link_units.sh &&

rm output/prisoners_temp.ttl &&

echo "Linking people" &&

cat output/prisoners_plain.ttl output/rank_links.ttl output/unit_linked_validated.ttl > output/prisoners_temp.ttl &&
python linker.py persons output/prisoners_temp.ttl output/persons_linked.ttl &&
rm output/prisoners_temp.ttl &&

sed -r 's/^(p:.*) cidoc:P70_documents (<.*>)/\2 cidoc:P70i_is_documented_in \1/' output/persons_linked.ttl > output/person_backlinks.ttl &&

# TODO: Link camps
# TODO: Link places using Arpa-linker

echo "Finishing prisoners" &&

cat output/prisoners_plain.ttl output/rank_links.ttl output/unit_linked_validated.ttl output/persons_linked.ttl > output/prisoners_full.ttl &&
rapper -i turtle output/prisoners_full.ttl -o turtle > output/prisoners.ttl &&

echo "Splitting to publishable and nonpublishable prisoners" &&
python prune_nonpublic.py output/prisoners.ttl &&
rm output/prisoners.ttl &&

echo "Generating people..." &&

echo "...Updating db with prisoners" &&
s-put http://localhost:3030/warsa/data http://ldf.fi/warsa/prisoners output/prisoners.ttl.public.ttl &&

echo "...Constructing people" &&
echo 'query=' | cat - sparql/construct_people.sparql | sed 's/&/%26/g' | curl -d @- http://localhost:3030/warsa/sparql -v > output/prisoner_people.ttl &&

echo "...Constructing documents links" &&
echo 'query=' | cat - sparql/construct_documents_links.sparql | sed 's/&/%26/g' | curl -d @- http://localhost:3030/warsa/sparql -v > output/prisoner_documents_links.ttl &&

echo "...Updating db with new people" &&
cat output/prisoner_people.ttl output/prisoner_documents_links.ttl > prisoners_temp.ttl &&
s-put http://localhost:3030/warsa/data http://ldf.fi/warsa/prisoner_persons output/prisoner_people.ttl &&
rm prisoners_temp.ttl &&

for construct in births promotions ranks unit_joinings captures disappearances
do
    echo "...Constructing $construct" &&
    echo 'query=' | cat - "sparql/construct_$construct.sparql" | sed 's/&/%26/g' | curl -d @- http://localhost:3030/warsa/sparql -v > "output/prisoner_$construct.ttl"
done &&

echo "...Deleting temp graph" &&
s-delete http://localhost:3030/warsa/data http://ldf.fi/warsa/prisoner_persons &&

echo "...Finished"
