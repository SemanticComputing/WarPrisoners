#!/usr/bin/env bash
python csv_to_rdf.py data/prisoners.csv data/new/ PRISONERS

python csv_to_rdf.py data/camps.csv data/new/ CAMPS

# TODO: Link camps
# TODO: Link persons using Arpa-linker and jellyfish
# TODO: Link military ranks using Arpa-linker
# TODO: Link military units using Arpa-linker
# TODO: Link places using Arpa-linker

