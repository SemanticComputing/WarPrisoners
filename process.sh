#!/usr/bin/env bash

command -v s-put >/dev/null 2>&1 || { echo >&2 "s-put is not available, aborting"; exit 1; }

echo "Converting to csv" &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/prisoners.xls --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/camps.xlsx --outdir data &&
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":44,34,76,1,1,11,true data/hospitals.xlsx --outdir data &&

echo "Converting to ttl" &&
python csv_to_rdf.py CAMPS data/camps.csv --outdata=data/new/camps.ttl --outschema=data/new/camp_schema.ttl &&
python csv_to_rdf.py HOSPITALS data/hospitals.csv --outdata=data/new/camps2.ttl &&

sed -r -i 's/\/prisoners\/r\_/\/prisoners\/camp_/g' data/new/camps.ttl &&
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/hospital_/g' data/new/camps2.ttl &&

cat data/new/camps.ttl data/new/camps2.ttl > data/new/camps.ttl &&
rm data/new/camps2.ttl &&

python csv_to_rdf.py PRISONERS data/prisoners.csv --outdata=data/new/prisoners.ttl --outschema=data/new/schema.ttl &&

echo "Linking ranks" &&

python linker.py ranks data/new/prisoners.ttl data/new/rank_links.ttl --endpoint "http://localhost:3030/warsa/sparql" &&

echo "Linking units" &&

cat data/new/prisoners.ttl data/new/rank_links.ttl > data/new/prisoners_temp.ttl &&

# Updated data needed for unit linking
s-put http://localhost:3030/warsa/data http://ldf.fi/warsa/prisoners data/new/prisoners_temp.ttl &&

echo 'query=' | cat - sparql/period.sparql | sed 's/&/%26/g' | curl -d @- http://localhost:3030/warsa/sparql -v > data/new/periods.ttl &&

./link_units.sh &&

rm data/new/prisoners_temp.ttl &&

echo "Linking people" &&

cat data/new/prisoners.ttl data/new/rank_links.ttl data/new/unit_linked_validated.ttl > data/new/prisoners_temp.ttl &&
python linker.py persons data/new/prisoners_temp.ttl data/new/persons_linked.ttl &&
rm data/new/prisoners_temp.ttl &&

# TODO: Link camps
# TODO: Link places using Arpa-linker

# Add testing triple:
#echo -e '\n<http://ldf.fi/warsa/prisoners/prisoner_858> <http://www.cidoc-crm.org/cidoc-crm/P70_documents> <http://ldf.fi/warsa/actors/person_p753249> .\n' >> data/new/prisoners.ttl &&

echo "Finishing" &&

cat data/new/prisoners.ttl data/new/rank_links.ttl data/new/unit_linked_validated.ttl data/new/persons_linked.ttl > data/new/prisoners_full.ttl &&
rapper -i turtle data/new/prisoners_full.ttl -o turtle > data/new/prisoners_final.ttl
