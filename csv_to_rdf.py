#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert Prisoners of War from CSV to RDF.
"""

import argparse
import logging
import os

import re
import iso8601

from rdflib import *
import pandas as pd

#################################

DATA_NAMESPACE = 'http://ldf.fi/warsa/prisoners/'
SCHEMA_NAMESPACE = 'http://ldf.fi/schema/warsa/prisoners/'

PROPERTY_MAPPING = {
    'suku- ja etunimet': {'uri': URIRef(SCHEMA_NAMESPACE + 'nimi'), 'name': 'Nimi'},
    'syntymäaika': {'uri': URIRef(SCHEMA_NAMESPACE + 'syntymaaika'), 'name': 'Syntymäaika'},
    'syntymäpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'syntymapaikka'), 'name': 'Syntymäpaikka'},
    'kotipaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'kotipaikka'), 'name': 'Kotipaikka'},
    'asuinpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'asuinpaikka'), 'name': 'Asuinpaikka'},
    'ammatti': {'uri': URIRef(SCHEMA_NAMESPACE + 'ammatti'), 'name': 'Ammatti'},
    'siviilisääty': {'uri': URIRef(SCHEMA_NAMESPACE + 'siviilisaaty'), 'name': 'Siviilisääty'},
}

INPUT_FILE_DIRECTORY = 'data/'
OUTPUT_FILE_DIRECTORY = 'data/new/'

DATA_FILE = 'surma.ttl'

#################################

log = logging.getLogger(__name__)

table = pd.read_csv(INPUT_FILE_DIRECTORY + 'vangit.csv', encoding='UTF-8', index_col=False, sep='\t', quotechar='"', na_values=['  '])

data = Graph()

column_headers = list(table)

for index in [0]:
    for column in range(0, len(column_headers)):
        column_name = column_headers[column]
        prisoner_uri = URIRef(DATA_NAMESPACE + 'prisoner_' + str(index))

        if column_name in PROPERTY_MAPPING:
            value = table.ix[index][column] if pd.notnull(table.ix[index][column]) else None

            if value:
                data.add((prisoner_uri, PROPERTY_MAPPING[column_name]['uri'], Literal(value)))

schema = Graph()
for prop in PROPERTY_MAPPING.values():
    schema.add((prop['uri'], RDFS.label, Literal(prop['name'])))

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
