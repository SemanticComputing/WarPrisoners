#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert Prisoners of War from CSV to RDF.
"""

import argparse
import datetime
import logging
import os

import re
import iso8601

from rdflib import *
import pandas as pd
import numpy as np

#################################

SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')

INSTANCE_CLASS = SCHEMA_NS.PrisonerOfWar

INPUT_FILE_DIRECTORY = 'data/'
OUTPUT_FILE_DIRECTORY = 'data/new/'

def convert_int(raw_value):
    if not raw_value:
        return raw_value
    try:
        value = int(raw_value)  # This cannot be directly converted on the DataFrame because of missing values.
        log.debug('Converted int: %s' % raw_value)
        return value
    except (ValueError, TypeError):
        log.error('Invalid value for int conversion: %s' % raw_value)
        return raw_value

def convert_dates(raw_date):
    """
    Convert date string to iso8601 date
    :param raw_date: raw date string from the CSV
    :return: ISO 8601 compliant date if can be parse, otherwise original date string
    """
    if not raw_date:
        return raw_date
    try:
        date = datetime.datetime.strptime(str(raw_date).strip(), '%d.%m.%Y').date()
        log.debug('Converted date: %s  to  %s' % (raw_date, date))
        return date
    except ValueError:
        log.error('Invalid value for date conversion: %s' % raw_date)
        return raw_date


PROPERTY_MAPPING = {
    'syntymäaika': {'uri': SCHEMA_NS.birth_date, 'converter': convert_dates,
                    'name_fi': 'Syntymäaika',
                    'name_en': 'Date of birth'},
    'syntymäpaikka': {'uri': SCHEMA_NS.birth_place, 'name_fi': 'Syntymäpaikka'},
    'kotipaikka': {'uri': SCHEMA_NS.home_place, 'name_fi': 'Kotipaikka'},
    'asuinpaikka': {'uri': SCHEMA_NS.residence_place, 'name_fi': 'Asuinpaikka'},
    'ammatti': {'uri': SCHEMA_NS.occupation, 'name_fi': 'Ammatti'},
    'siviilisääty': {'uri': SCHEMA_NS.marital_status, 'name_fi': 'Siviilisääty'},
    'lasten lkm': {'uri': SCHEMA_NS.amount_children, #'converter': convert_int,
                   'name_fi': 'Lasten lukumäärä'},
    'sotilas- arvo': {'uri': SCHEMA_NS.rank, 'name_fi': 'Sotilasarvo'},
    'joukko-osasto': {'uri': SCHEMA_NS.unit, 'name_fi': 'Joukko-osasto'},
    'vangiksi aika': {'uri': SCHEMA_NS.time_captured, 'converter': convert_dates,
                      'name_fi': 'Vangiksi jäämisen päivämäärä'},
    'vangiksi paikka': {'uri': SCHEMA_NS.place_captured, 'name_fi': 'Vangiksi jäämisen paikka'},
    'selvitys vangiksi jäämisestä': {'uri': SCHEMA_NS.explanation, 'name_fi': 'Selvitys vangiksi jäämisestä'},
    'palannut': {'uri': SCHEMA_NS.returned_date, 'converter': convert_dates,
                 'name_fi': 'Palaamisaika'},
    'kuollut': {'uri': SCHEMA_NS.death_date, 'converter': convert_dates,
                'name_fi': 'Kuolinaika'},
    'kuolinsyy': {'uri': SCHEMA_NS.cause_of_death, 'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'uri': SCHEMA_NS.death_place, 'name_fi': 'kuolinpaikka'},
    'hautauspaikka': {'uri': SCHEMA_NS.burial_place, 'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': SCHEMA_NS.camps_and_hospitals, 'name_fi': 'Leirit ja sairaalat'},
    ' muita tietoja': {'uri': SCHEMA_NS.other_information, 'name_fi': 'Muita tietoja'},
    'lisätietoja': {'uri': SCHEMA_NS.additional_information, 'name_fi': 'Lisätietoja'},
    'palanneiden kuolinaika': {'uri': SCHEMA_NS.death_date_of_returned, 'converter': convert_dates,
                               'name_fi': 'Palanneen kuolinaika'},
    'Sotavangit ry:n jäsen': {'uri': SCHEMA_NS.workspace, 'name_fi': 'Sotavangit ry:n jäsen'},
    'valokuva': {'uri': SCHEMA_NS.photograph, 'name_fi': 'Valokuva'},
    'paluukuulustelu-pöytäkirja; kjan lausunto; ilmoitus jääneistä sotavangeista; yht. sivumäärä':
        {'uri': SCHEMA_NS.minutes, 'name_fi': 'Paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä'},
    'kantakortti': {'uri': SCHEMA_NS.military_record, 'name_fi': 'Kantakortti'},
    'radiokatsaus': {'uri': SCHEMA_NS.radio_report, 'name_fi': 'Radiokatsaus'},
    'katoamis-dokumentit': {'uri': SCHEMA_NS.missing_person_documents, 'name_fi': 'Katoamisdokumentit'},
    'kuulustelija': {'uri': SCHEMA_NS.interrogator, 'name_fi': 'Kuulustelija'},
    'takavarikoitu omaisuus, arvo markoissa':
        {'uri': SCHEMA_NS.confiscated_possessions, 'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
    'suomenruotsalainen':
        {'uri': SCHEMA_NS.confiscated_possessions, 'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
}

# Some numbers and parentheses are also present in names
RE_NAME_SPLIT = r'([A-ZÅÄÖÉ/\-]+(?:\s+\(?E(?:NT)?[\.\s]+[A-ZÅÄÖ/\-]+)?\)?)\s*(?:(VON))?,?\s*([A-ZÅÄÖ/\- \(\)0-9,]*)'

#################################

argparser = argparse.ArgumentParser(description="Process war prisoners CSV", fromfile_prefix_chars='@')

argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                       choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

args = argparser.parse_args()

logging.basicConfig(filename='Prisoners.log',
                    filemode='a',
                    level=getattr(logging, args.loglevel.upper()),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log = logging.getLogger(__name__)

table = pd.read_csv(INPUT_FILE_DIRECTORY + 'vangit.csv', encoding='UTF-8', index_col=False, sep='\t', quotechar='"',
                    # parse_dates=[1], infer_datetime_format=True, dayfirst=True,
                    na_values=[' '], converters={'ammatti': lambda x: x.lower(), 'lasten lkm': convert_int})

table = table.fillna('').applymap(lambda x: x.strip() if type(x) == str else x)

data = Graph()

column_headers = list(table)

for index in range(len(table)):
    for column in range(len(column_headers)):

        column_name = column_headers[column]
        value = table.ix[index][column]

        prisoner_uri = DATA_NS['prisoner_' + str(index)]

        data.add((prisoner_uri, RDF.type, INSTANCE_CLASS))

        if column_name in PROPERTY_MAPPING:

            # if value:
            for single_value in (val.strip() for val in str(value).split(sep='/')):

                converter = PROPERTY_MAPPING[column_name].get('converter')
                single_value = converter(single_value) if converter else single_value

                # print(type(value))
                liter = Literal(single_value, datatype=XSD.date) if type(single_value) == datetime.date \
                    else Literal(single_value)
                data.add((prisoner_uri,
                          PROPERTY_MAPPING[column_name]['uri'],
                          Literal(single_value)))

        elif column_name == 'sukunimi ja etunimet':
            fullname = value.upper()

            namematch = re.search(RE_NAME_SPLIT, fullname)
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

            log.debug('Name %s was unified to form %s' % (value, fullname))


schema = Graph()
for prop in PROPERTY_MAPPING.values():
    if 'name_fi' in prop:
        schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
        schema.add((prop['uri'], RDF.type, RDF.Property))

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
