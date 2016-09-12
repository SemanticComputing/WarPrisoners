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

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')

INSTANCE_CLASS = SCHEMA_NS.PrisonerOfWar

PROPERTY_MAPPING = {
    # 'suku- ja etunimet': {'uri': URIRef('http://www.w3.org/2004/02/skos/core#prefLabel')},
    'syntymäaika': {'uri': SCHEMA_NS.birth_date, 'name_fi': 'Syntymäaika'},
    'syntymäpaikka': {'uri': SCHEMA_NS.birth_place, 'name_fi': 'Syntymäpaikka'},
    'kotipaikka': {'uri': SCHEMA_NS.home_place, 'name_fi': 'Kotipaikka'},
    'asuinpaikka': {'uri': SCHEMA_NS.residence_place, 'name_fi': 'Asuinpaikka'},
    'ammatti': {'uri': SCHEMA_NS.occupation, 'name_fi': 'Ammatti'},
    'siviilisääty': {'uri': SCHEMA_NS.marital_status, 'name_fi': 'Siviilisääty'},
    'lasten lkm': {'uri': SCHEMA_NS.amount_children, 'name_fi': 'Lasten lukumäärä'},
    'sotilas- arvo': {'uri': SCHEMA_NS.rank, 'name_fi': 'Sotilasarvo'},
    'joukko-osasto': {'uri': SCHEMA_NS.unit, 'name_fi': 'Joukko-osasto'},
    'vangiksi aika': {'uri': SCHEMA_NS.time_captured, 'name_fi': 'Vangiksi jäämisen päivämäärä'},
    'vangiksi paikka': {'uri': SCHEMA_NS.place_captured, 'name_fi': 'Vangiksi jäämisen paikka'},
    'selvitys vangiksi jäämisestä': {'uri': SCHEMA_NS.explanation, 'name_fi': 'Selvitys vangiksi jäämisestä'},
    'palannut': {'uri': SCHEMA_NS.returned_date, 'name_fi': 'Palaamisaika'},
    'kuollut': {'uri': SCHEMA_NS.death_date, 'name_fi': 'Kuolinaika'},
    'kuolinsyy': {'uri': SCHEMA_NS.cause_of_death, 'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'uri': SCHEMA_NS.death_place, 'name_fi': 'kuolinpaikka'},
    'hautauspaikka': {'uri': SCHEMA_NS.burial_place, 'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': SCHEMA_NS.camps_and_hospitals, 'name_fi': 'Leirit ja sairaalat'},
    ' muita tietoja': {'uri': SCHEMA_NS.other_information, 'name_fi': 'Muita tietoja'},
    'lisätietoja': {'uri': SCHEMA_NS.additional_information, 'name_fi': 'Lisätietoja'},
    'palanneiden kuolinaika': {'uri': SCHEMA_NS.death_date_of_returned, 'name_fi': 'Palanneen kuolinaika'},
    'työsarake': {'uri': SCHEMA_NS.workspace, 'name_fi': 'Työsarake'},
    'valokuva': {'uri': SCHEMA_NS.photograph, 'name_fi': 'Valokuva'},
    'paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä':
        {'uri': SCHEMA_NS.minutes, 'name_fi': 'Paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä'},
    'kantakortti': {'uri': SCHEMA_NS.military_record, 'name_fi': 'Kantakortti'},
    'radiokatsaus': {'uri': SCHEMA_NS.radio_report, 'name_fi': 'Radiokatsaus'},
    'katoamis-dokumentit': {'uri': SCHEMA_NS.missing_person_documents, 'name_fi': 'Katoamisdokumentit'},
    'kuulustelija': {'uri': SCHEMA_NS.interrogator, 'name_fi': 'Kuulustelija'},
    'takavarikoitu omaisuus, arvo markoissa':
        {'uri': SCHEMA_NS.confiscated_possessions, 'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
}

INPUT_FILE_DIRECTORY = 'data/'
OUTPUT_FILE_DIRECTORY = 'data/new/'

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
        prisoner_uri = DATA_NS['prisoner_' + str(index)]

        data.add((prisoner_uri, RDF.type, INSTANCE_CLASS))

        if column_name in PROPERTY_MAPPING:
            value = table.ix[index][column]

            if value and column_name == 'lasten lkm':
                value = int(value)  # This cannot be directly converted on the DataFrame because of missing values.

            if value:
                data.add((prisoner_uri, PROPERTY_MAPPING[column_name]['uri'], Literal(value)))

        elif column_name == 'suku- ja etunimet':
            fullname = table.ix[index][column].upper()

            name_parts = fullname.split()

            name_regex = r'([A-ZÅÄÖ/\-]+(?:\s+\(?E(?:NT)?[\.\s]+[A-ZÅÄÖ/\-]+)?\)?)\s*(?:(VON))?,?\s*([A-ZÅÄÖ/\-]*)'
            namematch = re.search(name_regex, fullname)
            (lastname, extra, firstnames) = namematch.groups() if namematch else (fullname, None, '')

            lastname = lastname.title()
            firstnames = firstnames.title()

            # Unify syntax for previous names
            prev_name_regex = r'([a-zA-ZåäöÅÄÖ/\-]{2}) +\(?(E(?:nt)?[\.\s]+)([a-zA-ZåäöÅÄÖ/\-]+)\)?'
            lastname = re.sub(prev_name_regex, r'\1 (ent. \3)', str(lastname))

            if extra:
                extra = extra.lower()
                lastname = ' '.join([extra, lastname])

            fullname = lastname

            if firstnames:
                data.add((prisoner_uri, SCHEMA_NS.firstnames, Literal(firstnames)))
                fullname += ', ' + firstnames.title()

            data.add((prisoner_uri, SCHEMA_NS.lastname, Literal(lastname)))
            data.add((prisoner_uri, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'), Literal(fullname)))


schema = Graph()
for prop in PROPERTY_MAPPING.values():
    if 'name_fi' in prop:
        schema.add((prop['uri'], RDFS.label, Literal(prop['name_fi'], lang='fi')))
        schema.add((prop['uri'], RDF.type, RDF.Property))

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
