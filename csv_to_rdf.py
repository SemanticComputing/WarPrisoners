#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert Prisoners of War from CSV to RDF using CIDOC CRM.
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
CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/elements/1.1/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')

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


def create_event(uri_suffix, event_type, participant_prop, participant, participant_name, labels, timespan=None, place=None, timespan_source=None,
                 place_source=None, event_source=None, extra_information=None):
    """
    Create an event or add information to an existing one (by using a previously used URI).

    :param uri_suffix:
    :param event_type: URIRef
    :param participant_prop:
    :param participant:
    :param participant_name:
    :param labels: list of label literals in different languages
    :param timespan: timespan tuple (begin, end) or single date
    :param place: string representing the target place
    :param timespan_source:
    :param place_source:
    :param event_source:
    :param extra_information: list of (predicate, object) tuples
    """

    uri = EVENTS_NS[uri_suffix]
    data.add((uri, RDF.type, event_type))
    data.add((uri, participant_prop, participant))

    labels = (Literal(labels[0].format(name=participant_name), lang='fi'),
              Literal(labels[1].format(name=participant_name), lang='en'))

    for label in labels:
        data.add((uri, SKOS.prefLabel, label))

    if event_source:
        data.add((uri, DC.source, event_source))

    if extra_information:
        for info in extra_information:
            data.add((uri,) + info)

    if timespan:
        if type(timespan) != tuple:
            timespan = (timespan, timespan)

        timespan_uri = EVENTS_NS[uri_suffix + '_timespan']
        label = (timespan[0] + ' - ' + timespan[1]) if timespan[0] != timespan[1] else timespan[0]

        data.add((uri, CIDOC['P4_has_time-span'], timespan_uri))
        data.add((timespan_uri, RDF.type, CIDOC['E52_Time-Span']))
        data.add((timespan_uri, CIDOC.P82a_begin_of_the_begin, Literal(timespan[0], datatype=XSD.date)))
        data.add((timespan_uri, CIDOC.P82b_end_of_the_end, Literal(timespan[1], datatype=XSD.date)))
        data.add((timespan_uri, SKOS.prefLabel, Literal(label)))

        if timespan_source:
            data.add((timespan_uri, DC.source, timespan_source))

    if place:
        property_uri = CIDOC['P7_took_place_at']

        if place_source:
            # USING (SEMI-)SINGLETON PROPERTIES TO DENOTE SOURCE
            property_uri = DATA_NS['took_place_at_' + place + '_' + place_source]

            data.add((property_uri, DC.source, place_source))
            data.add((property_uri, RDFS.subClassOf, CIDOC['P7_took_place_at']))

        data.add((uri, property_uri, place))

class RDFMapper:

    def __init__(self, mapping, instance_class):
        self.mapping = mapping
        self.instance_class = instance_class

    def _unify_name(self, original_name):

        fullname = original_name.upper()

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
            fullname += ', ' + firstnames.title()

        log.debug('Name %s was unified to form %s' % (original_name, fullname))
        return firstnames, lastname, fullname

    def map_row_to_rdf(self, entity_uri, row):

        (firstnames, lastname, fullname) = self._unify_name(row[0])

        if firstnames:
            data.add((entity_uri, SCHEMA_NS.firstnames, Literal(firstnames)))

        data.add((entity_uri, SCHEMA_NS.lastname, Literal(lastname)))
        data.add((entity_uri, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'), Literal(fullname)))

        for column_name in self.mapping:

            value = row[column_name]

            data.add((entity_uri, RDF.type, self.instance_class))

            slash_separated = self.mapping[column_name].get('slash_separated')

            # Make an iterable of all values in this field
            # TODO: Handle columns separated by ;

            values = (val.strip() for val in str(value).split(sep='/')) if slash_separated else [str(value).strip()]

            for single_value in values:

                # Take sources for each value if present

                if slash_separated:
                    RE_SOURCE_SPLIT = r'(.+) \(([^\(\)]+)\)(.*)'
                    sourcematch = re.search(RE_SOURCE_SPLIT, single_value)
                    (single_value, sources, trash) = sourcematch.groups() if sourcematch else (single_value, None, None)

                    sources = (s.strip() for s in sources.split(',')) if sources else []

                    if trash:
                        log.warning('Found some content after sources: %s' % trash)

                # Convert value to some format

                converter = self.mapping[column_name].get('converter')
                single_value = converter(single_value) if converter else single_value

                if single_value:
                    event = self.mapping[column_name].get('event')

                    if event:

                        # Create event

                        event_prop = self.mapping[column_name].get('event_prop')
                        event_uri_suffix = self.mapping[column_name].get('event_uri_suffix')
                        participant_prop = self.mapping[column_name].get('participant_prop')
                        event_labels = self.mapping[column_name].get('event_labels')
                        event_information = self.mapping[column_name].get('event_information')

                        create_event('prisoner_' + str(index) + event_uri_suffix, event, participant_prop,
                                     entity_uri, fullname, event_labels, **{event_prop: single_value,
                                     'extra_information': event_information})

                    else:

                        # Create literal

                        liter = Literal(single_value, datatype=XSD.date) if type(single_value) == datetime.date \
                            else Literal(single_value)

                        data.add((entity_uri,
                                  self.mapping[column_name]['uri'],
                                  Literal(liter)))


PROPERTY_MAPPING = {
    'syntymäaika': {'converter': convert_dates,
                    'slash_separated': True,
                    'event': CIDOC.E67_Birth,
                    'event_prop': 'timespan',
                    'participant_prop': CIDOC.P98_brought_into_life,
                    'event_uri_suffix': '_birth',
                    'event_labels': ('Henkilö {name} syntyi', 'Person {name} was born'),
                    },
    'syntymäpaikka': {'converter': Literal,
                      'slash_separated': True,
                      'event': CIDOC.E67_Birth,
                      'event_prop': 'place',
                      'participant_prop': CIDOC.P98_brought_into_life,
                      'event_uri_suffix': '_birth',
                      'event_labels': ('Henkilö {name} syntyi', 'Person {name} was born'),
                      },
    'kotipaikka': {'uri': SCHEMA_NS.home_place, 'slash_separated': True,
                   'name_fi': 'Kotikunta',
                   'name_en': 'Municipality of home'
                   },
    'asuinpaikka': {'uri': SCHEMA_NS.residence_place, 'name_fi': 'Asuinpaikka', 'slash_separated': True},
    'ammatti': {'uri': SCHEMA_NS.occupation, 'name_fi': 'Ammatti', 'slash_separated': True},
    'siviilisääty': {'uri': SCHEMA_NS.marital_status, 'name_fi': 'Siviilisääty', 'slash_separated': True},
    'lasten lkm': {'uri': SCHEMA_NS.amount_children, #'converter': convert_int,
                   'name_fi': 'Lasten lukumäärä', 'slash_separated': True},
    'sotilas- arvo': {'uri': SCHEMA_NS.rank, 'name_fi': 'Sotilasarvo', 'slash_separated': True},
    'joukko-osasto': {'uri': SCHEMA_NS.unit, 'name_fi': 'Joukko-osasto', 'slash_separated': False},
    'vangiksi aika': {'uri': SCHEMA_NS.time_captured, 'converter': convert_dates, 'slash_separated': True,
                      'name_fi': 'Vangiksi jäämisen päivämäärä'},
    'vangiksi paikka': {'uri': SCHEMA_NS.place_captured, 'slash_separated': True,
                        'name_fi': 'Vangiksi jäämisen paikka'},
    'selvitys vangiksi jäämisestä': {'uri': SCHEMA_NS.explanation, 'slash_separated': False,
                                     'name_fi': 'Selvitys vangiksi jäämisestä'},
    'palannut': {'uri': SCHEMA_NS.returned_date, 'converter': convert_dates, 'slash_separated': True,
                 'name_fi': 'Palaamisaika'},
    'kuollut': {'converter': convert_dates,
                'slash_separated': True,
                'event': CIDOC.E69_Death,
                'event_prop': 'timespan',
                'participant_prop': CIDOC.P100_was_death_of,
                'event_uri_suffix': '_death',
                'event_labels': ('Henkilö {name} kuoli', 'Person {name} died'),
                },
    'kuolinsyy': {'uri': SCHEMA_NS.cause_of_death, 'slash_separated': False,
                  'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'slash_separated': False,  # epämääräinen muotoilu
                     'converter': Literal,
                     'event': CIDOC.E69_Death,
                     'event_prop': 'place',
                     'participant_prop': CIDOC.P100_was_death_of,
                     'event_uri_suffix': '_death',
                     'event_labels': ('Henkilö {name} kuoli', 'Person {name} died'),
                     },
    'hautauspaikka': {'uri': SCHEMA_NS.burial_place, 'slash_separated': False, 'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': SCHEMA_NS.camps_and_hospitals, 'slash_separated': False,
                           'name_fi': 'Leirit ja sairaalat'},
    ' muita tietoja': {'uri': SCHEMA_NS.other_information, 'slash_separated': False,
                       'name_fi': 'Muita tietoja'},
    'lisätietoja': {'uri': SCHEMA_NS.additional_information, 'slash_separated': False,
                    'name_fi': 'Lisätietoja'},
    'palanneiden kuolinaika': {'uri': SCHEMA_NS.death_date_of_returned, 'converter': convert_dates,
                               'slash_separated': False,
                               'name_fi': 'Palanneen kuolinaika'},
    'Sotavangit ry:n jäsen': {'uri': SCHEMA_NS.association,
                              'converter': convert_dates,
                              'slash_separated': True,
                              'event': CIDOC.E85_Joining,
                              'event_prop': 'timespan',
                              'participant_prop': CIDOC.P143_joined,
                              'event_uri_suffix': '_prisoner_association',
                              'event_information': [(CIDOC.P144_joined_with, DATA_NS.Prisoner_association)],
                              'event_labels': ('Henkilö {name} liittyi ryhmään', 'Person {name} joined group'),
                              },
    'valokuva': {'uri': SCHEMA_NS.photograph, 'slash_separated': False, 'name_fi': 'Valokuva'},
    'paluukuulustelu-pöytäkirja; kjan lausunto; ilmoitus jääneistä sotavangeista; yht. sivumäärä':
        {'uri': SCHEMA_NS.minutes, 'slash_separated': True,
         'name_fi': 'Paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä'},
    'kantakortti': {'uri': SCHEMA_NS.military_record, 'slash_separated': False, 'name_fi': 'Kantakortti'},
    'radiokatsaus': {'uri': SCHEMA_NS.radio_report, 'slash_separated': False, 'name_fi': 'Radiokatsaus'},
    'katoamis-dokumentit': {'uri': SCHEMA_NS.missing_person_documents, 'slash_separated': False,
                            'name_fi': 'Katoamisdokumentit'},
    'kuulustelija': {'uri': SCHEMA_NS.interrogator, 'slash_separated': False, 'name_fi': 'Kuulustelija'},
    'takavarikoitu omaisuus, arvo markoissa':
        {'uri': SCHEMA_NS.confiscated_possessions, 'slash_separated': True,
         'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
    'suomenruotsalainen':
        {'uri': SCHEMA_NS.confiscated_possessions, 'slash_separated': True,
         'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
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

mapper = RDFMapper(PROPERTY_MAPPING, SCHEMA_NS.PrisonerOfWar)

for index in range(len(table)):
    prisoner_uri = DATA_NS['prisoner_' + str(index)]

    mapper.map_row_to_rdf(prisoner_uri, table.ix[index])

schema = Graph()
for prop in PROPERTY_MAPPING.values():
    if 'name_fi' in prop:
        schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
        schema.add((prop['uri'], RDF.type, RDF.Property))

data.bind("p", "http://ldf.fi/warsa/prisoners/")
data.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
data.bind("skos", "http://www.w3.org/2004/02/skos/core#")

schema.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
