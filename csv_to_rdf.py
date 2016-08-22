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
    'suku- ja etunimet': {'uri': URIRef(SCHEMA_NAMESPACE + 'name_fi'), 'name_fi': 'Nimi'},
    'syntymäaika': {'uri': URIRef(SCHEMA_NAMESPACE + 'birth_date'), 'name_fi': 'Syntymäaika'},
    'syntymäpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'birth_place'), 'name_fi': 'Syntymäpaikka'},
    'kotipaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'home_place'), 'name_fi': 'Kotipaikka'},
    'asuinpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'residence_place'), 'name_fi': 'Asuinpaikka'},
    'ammatti': {'uri': URIRef(SCHEMA_NAMESPACE + 'occupation'), 'name_fi': 'Ammatti'},
    'siviilisääty': {'uri': URIRef(SCHEMA_NAMESPACE + 'martial_status'), 'name_fi': 'Siviilisääty'},
    'lasten lkm': {'uri': URIRef(SCHEMA_NAMESPACE + 'amount_children'), 'name_fi': 'Lasten lukumäärä'},
    'sotilas- arvo': {'uri': URIRef(SCHEMA_NAMESPACE + 'rank'), 'name_fi': 'Sotilasarvo'},
    'joukko-osasto': {'uri': URIRef(SCHEMA_NAMESPACE + 'unit'), 'name_fi': 'Joukko-osasto'},
    'vangiksi aika': {'uri': URIRef(SCHEMA_NAMESPACE + 'time_captured'), 'name_fi': 'Vangiksi jäämisen päivämäärä'},
    'vangiksi paikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'place_captured'), 'name_fi': 'Vangiksi jäämisen paikka'},
    'selvitys vangiksi jäämisestä': {'uri': URIRef(SCHEMA_NAMESPACE + 'explanation'),
                                     'name_fi': 'Selvitys vangiksi jäämisestä'},
    'palannut': {'uri': URIRef(SCHEMA_NAMESPACE + 'returned_date'), 'name_fi': 'Palaamisen päivämäärä'},
    'kuollut': {'uri': URIRef(SCHEMA_NAMESPACE + 'death_date'), 'name_fi': 'Kuolinpäivämäärä'},
    'kuolinsyy': {'uri': URIRef(SCHEMA_NAMESPACE + 'cause_of_death'), 'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'death_place'), 'name_fi': 'kuolinpaikka'},
    'hautauspaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'burial_place'), 'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': URIRef(SCHEMA_NAMESPACE + 'camps_and_hospitals'), 'name_fi': 'Leirit ja sairaalat'},
    '': {'uri': URIRef(SCHEMA_NAMESPACE + ''), 'name_fi': ''},
    '': {'uri': URIRef(SCHEMA_NAMESPACE + ''), 'name_fi': ''},
}

INPUT_FILE_DIRECTORY = 'data/'
OUTPUT_FILE_DIRECTORY = 'data/new/'

DATA_FILE = 'surma.ttl'

#################################

logging.basicConfig(filename='Prisoners.log',
                    filemode='a',
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log = logging.getLogger(__name__)

table = pd.read_csv(INPUT_FILE_DIRECTORY + 'vangit.csv', encoding='UTF-8', index_col=False, sep='\t', quotechar='"', na_values=['  '])

data = Graph()

column_headers = list(table)

print(column_headers)

for index in range(len(table)):
    for column in range(len(column_headers)):
        column_name = column_headers[column]
        prisoner_uri = URIRef(DATA_NAMESPACE + 'prisoner_' + str(index))

        if column_name in PROPERTY_MAPPING:
            value = table.ix[index][column] if pd.notnull(table.ix[index][column]) else None

            if value:
                data.add((prisoner_uri, PROPERTY_MAPPING[column_name]['uri'], Literal(value)))

schema = Graph()
for prop in PROPERTY_MAPPING.values():
    schema.add((prop['uri'], RDFS.label, Literal(prop['name_fi'], lang='fi')))
    schema.add((prop['uri'], RDF.type, RDF.Property))

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
