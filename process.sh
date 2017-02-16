#!/usr/bin/env bash
python csv_to_rdf.py data/prisoners.csv data/new/ PRISONERS

python csv_to_rdf.py data/camps.csv data/new/ CAMPS