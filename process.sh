#!/usr/bin/env bash
python csv_to_rdf.py PRISONERS data/prisoners.csv --outdata=data/new/prisoners.ttl --outschema=data/new/schema.ttl
python csv_to_rdf.py CAMPS data/camps.csv --outdata=data/new/camps.ttl --outschema=data/new/camp_schema.ttl

python linker.py ranks data/new/prisoners.ttl data/new/prisoners_linked.ttl --endpoint "http://localhost:3030/warsa/sparql"

# TODO: Link persons using Arpa-linker and jellyfish

# TODO: Link camps
# TODO: Link places using Arpa-linker

