#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert Prisoners of War from CSV to RDF.
"""

import argparse
import logging
from math import nan
import os

import re
import iso8601

from rdflib import *
import pandas as pd

#################################

NAMESPACE = 'http://ldf.fi/warsa/prisoners/'
PROPERTY_MAPPING = {
    'suku- ja etunimet': {'uri': URIRef(NAMESPACE + 'nimi'), 'name': 'Nimi'},
    'syntymäaika': {'uri': URIRef(NAMESPACE + 'syntymaaika'), 'name': 'Syntymäaika'},
    'syntymäpaikka': {'uri': URIRef(NAMESPACE + 'syntymapaikka'), 'name': 'Syntymäpaikka'},
    'kotipaikka': {'uri': URIRef(NAMESPACE + 'kotipaikka'), 'name': 'Kotipaikka'},
    'asuinpaikka': {'uri': URIRef(NAMESPACE + 'asuinpaikka'), 'name': 'Asuinpaikka'},
    'ammatti': {'uri': URIRef(NAMESPACE + 'ammatti'), 'name': 'Ammatti'},
    'siviilisääty': {'uri': URIRef(NAMESPACE + 'siviilisaaty'), 'name': 'Siviilisääty'},
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
        prisoner_uri = URIRef(NAMESPACE + 'prisoner_' + str(index))

        if column_name in PROPERTY_MAPPING:
            value = table.ix[index][column] if pd.notnull(table.ix[index][column]) else None

            if value:
                log.warning('Object type: {type}, value: {value}'.format(type=type(value), value=value))

                data.add((prisoner_uri, PROPERTY_MAPPING[column_name]['uri'], Literal(value)))

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
