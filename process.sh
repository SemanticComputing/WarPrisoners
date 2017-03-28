#!/usr/bin/env bash
python csv_to_rdf.py data/prisoners.csv data/new/ PRISONERS
python csv_to_rdf.py data/camps.csv data/new/ CAMPS

python linker.py ranks data/new/prisoners.ttl data/new/prisoners_linked.ttl --endpoint "http://localhost:3030/warsa/sparql"

# TODO: Link military units using Arpa-linker
# TODO: Link persons using Arpa-linker and jellyfish

# TODO: Link camps
# TODO: Link places using Arpa-linker

