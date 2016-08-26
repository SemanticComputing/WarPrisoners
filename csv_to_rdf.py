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
import numpy as np

#################################

DATA_NAMESPACE = 'http://ldf.fi/warsa/prisoners/'
SCHEMA_NAMESPACE = 'http://ldf.fi/schema/warsa/prisoners/'

INSTANCE_CLASS = URIRef(SCHEMA_NAMESPACE + 'PrisonerOfWar')

PROPERTY_MAPPING = {
    'suku- ja etunimet': {'uri': URIRef('http://www.w3.org/2004/02/skos/core#prefLabel')},
    'syntymäaika': {'uri': URIRef(SCHEMA_NAMESPACE + 'birth_date'), 'name_fi': 'Syntymäaika'},
    'syntymäpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'birth_place'), 'name_fi': 'Syntymäpaikka'},
    'kotipaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'home_place'), 'name_fi': 'Kotipaikka'},
    'asuinpaikka': {'uri': URIRef(SCHEMA_NAMESPACE + 'residence_place'), 'name_fi': 'Asuinpaikka'},
    'ammatti': {'uri': URIRef(SCHEMA_NAMESPACE + 'occupation'), 'name_fi': 'Ammatti'},
    'siviilisääty': {'uri': URIRef(SCHEMA_NAMESPACE + 'marital_status'), 'name_fi': 'Siviilisääty'},
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
    ' muita tietoja': {'uri': URIRef(SCHEMA_NAMESPACE + 'additional_information'), 'name_fi': 'Muita tietoja'},
    'palanneiden kuolinaika': {'uri': URIRef(SCHEMA_NAMESPACE + 'death_date_of_returned'), 'name_fi': 'Palanneen kuolinaika'},
    'työsarake': {'uri': URIRef(SCHEMA_NAMESPACE + 'workspace'), 'name_fi': 'Työsarake'},
    'valokuva': {'uri': URIRef(SCHEMA_NAMESPACE + 'photograph'), 'name_fi': 'Valokuva'},
    'paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä':
        {'uri': URIRef(SCHEMA_NAMESPACE + 'minutes'), 'name_fi': 'Paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä'},
    'kantakortti': {'uri': URIRef(SCHEMA_NAMESPACE + 'military_record'), 'name_fi': 'Kantakortti'},
    'radiokatsaus': {'uri': URIRef(SCHEMA_NAMESPACE + 'radio_report'), 'name_fi': 'Radiokatsaus'},
    'katoamis-dokumentit': {'uri': URIRef(SCHEMA_NAMESPACE + 'missing_person_documents'), 'name_fi': 'Katoamisdokumentit'},
    'kuulustelija': {'uri': URIRef(SCHEMA_NAMESPACE + 'interrogator'), 'name_fi': 'Kuulustelija'},
    'takavarikoitu omaisuus, arvo markoissa':
        {'uri': URIRef(SCHEMA_NAMESPACE + 'confiscated_possessions'), 'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
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

table = pd.read_csv(INPUT_FILE_DIRECTORY + 'vangit.csv', encoding='UTF-8', index_col=False, sep='\t', quotechar='"',
                    na_values=[' '], converters={'ammatti': lambda x: x.lower()})

table = table.fillna('').applymap(lambda x: x.strip() if type(x) == str else x)

data = Graph()

column_headers = list(table)

for index in range(len(table)):
    for column in range(len(column_headers)):

        column_name = column_headers[column]
        prisoner_uri = URIRef(DATA_NAMESPACE + 'prisoner_' + str(index))

        data.add((prisoner_uri, RDF.type, INSTANCE_CLASS))

        if column_name in PROPERTY_MAPPING:
            value = table.ix[index][column]

            if value and column_name == 'lasten lkm':
                value = int(value)  # This cannot be directly converted on the DataFrame because of missing values.

            if value:
                data.add((prisoner_uri, PROPERTY_MAPPING[column_name]['uri'], Literal(value)))

schema = Graph()
for prop in PROPERTY_MAPPING.values():
    if 'name_fi' in prop:
        schema.add((prop['uri'], RDFS.label, Literal(prop['name_fi'], lang='fi')))
        schema.add((prop['uri'], RDF.type, RDF.Property))

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
