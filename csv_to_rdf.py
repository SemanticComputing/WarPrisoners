#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert Prisoners of War from CSV to RDF using CIDOC CRM.
"""

import argparse

import pandas as pd
from rdflib import URIRef

from converters import *
from mapping import PRISONER_MAPPING

CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/elements/1.1/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')

INPUT_FILE_DIRECTORY = 'data/'
OUTPUT_FILE_DIRECTORY = 'data/new/'


class RDFMapper:
    """
    Map tabular data (currently pandas DataFrame) to RDF. Create a class instance of each row.
    """

    def __init__(self, mapping, instance_class):
        self.mapping = mapping
        self.instance_class = instance_class

    def map_row_to_rdf(self, entity_uri, row):
        """
        Map a single row to RDF.

        :param entity_uri: URI of the instance being created
        :param row: tabular data
        :return:
        """

        row_rdf = Graph()

        (firstnames, lastname, fullname) = convert_person_name(row[0])

        if firstnames:
            row_rdf.add((entity_uri, FOAF.givenName, Literal(firstnames)))

        row_rdf.add((entity_uri, FOAF.familyName, Literal(lastname)))
        row_rdf.add((entity_uri, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'), Literal(fullname)))

        for column_name in self.mapping:

            # TODO: Don't throw KeyError if column_name is not found??

            value = row[column_name]

            row_rdf.add((entity_uri, RDF.type, self.instance_class))

            slash_separated = self.mapping[column_name].get('slash_separated')

            # Make an iterable of all values in this field
            # TODO: Handle columns separated by ;

            # values = (val.strip() for val in str(value).split(sep='/')) if slash_separated else [str(value).strip()]
            values = (val.strip() for val in re.split(r'\s/\s', str(value))) if slash_separated else \
                [str(value).strip()]

            for single_value in values:

                # Take sources for each value if present

                sources = ''
                if slash_separated:
                    sourcematch = re.search(r'(.+) \(([^\(\)]+)\)(.*)', single_value)
                    (single_value, sources, trash) = sourcematch.groups() if sourcematch else (single_value, None, None)

                    if sources:
                        log.debug('Found sources: %s' % sources)
                        sources = (Literal(s.strip()) for s in sources.split(','))
                        # TODO: Use resources instead of literals

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

                        row_rdf += create_event('prisoner_' + str(index) + event_uri_suffix, event, participant_prop,
                                                entity_uri, fullname, event_labels, extra_information=event_information,
                                                prop_sources=sources,
                                                **{event_prop: single_value})

                    else:
                        # Create literal

                        liter = Literal(single_value, datatype=XSD.date) if type(single_value) == datetime.date \
                            else Literal(single_value)

                        row_rdf.add((entity_uri,
                                     self.mapping[column_name]['uri'],
                                     Literal(liter)))

        return row_rdf

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

mapper = RDFMapper(PRISONER_MAPPING, SCHEMA_NS.PrisonerOfWar)

for index in range(len(table)):
    prisoner_uri = DATA_NS['prisoner_' + str(index)]

    data += mapper.map_row_to_rdf(prisoner_uri, table.ix[index])

schema = Graph()
for prop in PRISONER_MAPPING.values():
    if 'name_fi' in prop:
        schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
        schema.add((prop['uri'], RDF.type, RDF.Property))

data.bind("p", "http://ldf.fi/warsa/prisoners/")
data.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
data.bind("skos", "http://www.w3.org/2004/02/skos/core#")
data.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
data.bind("foaf", 'http://xmlns.com/foaf/0.1/')
data.bind("bioc", 'http://ldf.fi/schema/bioc/')

schema.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")
schema.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
schema.bind("foaf", 'http://xmlns.com/foaf/0.1/')
schema.bind("bioc", 'http://ldf.fi/schema/bioc/')

data.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "prisoners.ttl")
schema.serialize(format="turtle", destination=OUTPUT_FILE_DIRECTORY + "schema.ttl")
