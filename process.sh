#!/usr/bin/env bash
python csv_to_rdf.py CAMPS data/camps.csv --outdata=data/new/camps.ttl --outschema=data/new/camp_schema.ttl &&
python csv_to_rdf.py HOSPITALS data/hospitals.csv --outdata=data/new/camps2.ttl &&

sed -r -i 's/\/prisoners\/r\_/\/prisoners\/camp_/g' data/new/camps.ttl &&
sed -r -i 's/\/prisoners\/r\_/\/prisoners\/hospital_/g' data/new/camps2.ttl &&

cat data/new/camps.ttl data/new/camps2.ttl > data/new/camps.ttl &&
rm data/new/camps2.ttl

python csv_to_rdf.py PRISONERS data/prisoners.csv --outdata=data/new/prisoners.ttl --outschema=data/new/schema.ttl &&
python linker.py ranks data/new/prisoners.ttl data/new/rank_links.ttl --endpoint "http://localhost:3030/warsa/sparql" &&

# TODO: Link persons using Arpa-linker and jellyfish

# TODO: Link camps
# TODO: Link places using Arpa-linker

cat data/new/prisoners.ttl data/new/rank_links.ttl > data/new/prisoners_final.ttl

