#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert Prisoners of War from CSV to RDF using CIDOC CRM.
"""

import argparse
import datetime
import logging
import re

import pandas as pd
from rdflib import URIRef, Namespace, Graph, RDF, Literal
from rdflib import XSD

from converters import convert_int, convert_person_name, convert_dates
from mapping import PRISONER_MAPPING

from csv2rdf import CSV2RDF

CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/elements/1.1/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')


class RDFMapper:
    """
    Map tabular data (currently pandas DataFrame) to RDF. Create a class instance of each row.
    """

    def __init__(self, mapping, instance_class, loglevel='WARNING'):
        self.mapping = mapping
        self.instance_class = instance_class
        self.table = None
        self.data = Graph()
        self.schema = Graph()
        logging.basicConfig(filename='rdfmapper.log',
                            filemode='a',
                            level=getattr(logging, loglevel),
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.log = logging.getLogger(__name__)

    def read_value_with_source(self, orig_value):
        """
        Read a value with source given in the end in parenthesis

        :param orig_value: string in format "value (source)"
        :return: value, sources
        """

        sourcematch = re.search(r'(.+) \(([^()]+)\)(.*)', orig_value)
        (value, sources, trash) = sourcematch.groups() if sourcematch else (orig_value, None, None)

        if sources:
            self.log.debug('Found sources: %s' % sources)
            sources = [s.strip() for s in sources.split(',')]

        if trash:
            self.log.warning('Found some content after sources, reverting to original: %s' % trash)
            value = orig_value

        return value.strip(), sources or []

    def read_semicolon_separated(self, orig_value):
        """
        Read semicolon separated values (with possible sources and date range)

        :param orig_value: string in format "source: value date1-date2", or just "value"
        :return: value, sources
        """

        if ': ' in orig_value:
            try:
                (sources, value) = orig_value.split(': ')
            except ValueError as error:
                self.log.error('Semicolon separated: %s caused error "%s"' % (orig_value, error))
                (sources, value) = ('', orig_value)
        else:
            (sources, value) = ('', orig_value)

        datematch = re.search(r'(.+) ([0-9xX.]{5,})-([0-9xX.]{5,})', value)
        (value, date_begin, date_end) = datematch.groups() if datematch else (value, None, None)

        if date_begin:
            date_begin = convert_dates(date_begin)

        if date_end:
            date_end = convert_dates(date_end)

        if sources:
            self.log.debug('Found sources: %s' % sources)
            sources = [s.strip() for s in sources.split(',')]

        if date_begin or date_end:
            self.log.debug('Found dates for value: %s - %s' % (date_begin, date_end))

        return value, sources or [], date_begin, date_end

    def map_row_to_rdf(self, entity_uri, row):
        """
        Map a single row to RDF.

        :param entity_uri: URI of the instance being created
        :param row: tabular data
        :return:
        """
        reification_template = '{entity}_{prop}_{id}_reification_{reason}'

        row_rdf = Graph()

        # Handle first and last names

        (firstnames, lastname, fullname) = convert_person_name(row[0])

        original_name = row[0].strip()

        if firstnames:
            row_rdf.add((entity_uri, FOAF.givenName, Literal(firstnames)))

        row_rdf.add((entity_uri, FOAF.familyName, Literal(lastname)))
        row_rdf.add((entity_uri, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'), Literal(fullname)))
        row_rdf.add((entity_uri, SCHEMA_NS.original_name, Literal(original_name)))

        # Loop through the mapping dict and convert data to RDF
        for column_name in self.mapping:

            mapping = self.mapping[column_name]

            value = row[column_name]

            row_rdf.add((entity_uri, RDF.type, self.instance_class))

            separator = mapping.get('value_separator')

            # Make an iterable of all values in this field

            # values = (val.strip() for val in re.split(r'\s/\s', str(value))) if separator == '/' else \
            if separator == '/':
                values = (val.strip() for val in re.split(r'(?: /)|(?:/ )', str(value)) if val)
            elif separator == ';':
                values = (val.strip() for val in re.split(';', str(value)) if val)
            else:
                values = [str(value).strip()]

            for index, value in enumerate(values):

                sources = []
                date_begin = None
                date_end = None

                if separator == '/':
                    value, sources = self.read_value_with_source(value)
                elif separator == ';':
                    value, sources, date_begin, date_end = self.read_semicolon_separated(value)

                converter = mapping.get('converter')
                value = converter(value) if converter else value

                if value:
                    liter = Literal(value, datatype=XSD.date) if type(value) == datetime.date else Literal(value)
                    row_rdf.add((entity_uri, mapping['uri'], liter))

                    for source in sources:
                        reification_uri = DATA_NS[reification_template.format(entity=entity_uri.split('/')[-1],
                                                                              prop=mapping['uri'].split('/')[-1],
                                                                              id=index,
                                                                              reason='source')]
                        row_rdf.add((reification_uri, RDF.subject, entity_uri))
                        row_rdf.add((reification_uri, RDF.predicate, mapping['uri']))
                        row_rdf.add((reification_uri, RDF.object, liter))
                        row_rdf.add((reification_uri, RDF.type, RDF.Statement))
                        row_rdf.add((reification_uri, DC.source, Literal(source)))

                    if date_begin or date_end:
                        reification_uri = DATA_NS[reification_template.format(entity=entity_uri.split('/')[-1],
                                                                              prop=mapping['uri'].split('/')[-1],
                                                                              id=index,
                                                                              reason='daterange')]
                        row_rdf.add((reification_uri, RDF.subject, entity_uri))
                        row_rdf.add((reification_uri, RDF.predicate, mapping['uri']))
                        row_rdf.add((reification_uri, RDF.object, liter))
                        row_rdf.add((reification_uri, RDF.type, RDF.Statement))
                        row_rdf.add((reification_uri, SCHEMA_NS.date_begin, Literal(date_begin)))
                        row_rdf.add((reification_uri, SCHEMA_NS.date_end, Literal(date_end)))

        return row_rdf

    def read_csv(self, csv_input):
        """
        Read in a CSV files using pandas.read_csv

        :param csv_input: CSV input (filename or buffer)
        """
        csv_data = pd.read_csv(csv_input, encoding='UTF-8', index_col=False, sep='\t', quotechar='"',
                               # parse_dates=[1], infer_datetime_format=True, dayfirst=True,
                               na_values=[' '], converters={'ammatti': lambda x: x.lower()})

        self.table = csv_data.fillna('').applymap(lambda x: x.strip() if type(x) == str else x)

    def serialize(self, destination_data, destination_schema):
        """
        Serialize RDF graphs

        :param destination_data: serialization destination for data
        :param destination_schema: serialization destination for schema
        :return: output from rdflib.Graph.serialize
        """
        self.data.bind("p", "http://ldf.fi/warsa/prisoners/")
        self.data.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
        self.data.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.data.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.data.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.data.bind("bioc", 'http://ldf.fi/schema/bioc/')

        self.schema.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
        self.schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.schema.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.schema.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.schema.bind("bioc", 'http://ldf.fi/schema/bioc/')

        data = self.data.serialize(format="turtle", destination=destination_data)
        schema = self.schema.serialize(format="turtle", destination=destination_schema)

        return data, schema  # Mainly for testing purposes

    def process_rows(self):
        """
        Loop through CSV rows and convert them to RDF
        """
        # column_headers = list(self.table)
        #
        for index in range(len(self.table)):
            prisoner_uri = DATA_NS['prisoner_' + str(index)]
            self.data += self.map_row_to_rdf(prisoner_uri, self.table.ix[index])

        for prop in PRISONER_MAPPING.values():
            self.schema.add((prop['uri'], RDF.type, RDF.Property))
            if 'name_fi' in prop:
                self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
            if 'name_en' in prop:
                self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_en'], lang='en')))


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Process war prisoners CSV", fromfile_prefix_chars='@')

    argparser.add_argument("input", help="Input CSV file")
    argparser.add_argument("output", help="Output location to serialize RDF files to")
    argparser.add_argument("mode", help="CSV conversion mode", default="PRISONERS", choices=["PRISONERS", "CAMPS"])
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

    args = argparser.parse_args()

    output_dir = args.output + '/' if args.output[-1] != '/' else args.output

    if args.mode == "PRISONERS":
        mapper = RDFMapper(PRISONER_MAPPING, SCHEMA_NS.PrisonerOfWar, loglevel=args.loglevel.upper())
        mapper.read_csv(args.input)

        mapper.process_rows()

        mapper.serialize(output_dir + "prisoners.ttl", output_dir + "schema.ttl")

    elif args.mode == "CAMPS":
        mapper = CSV2RDF()
        mapper.read_csv(args.input, **{'sep': '\t'})
        mapper.convert_to_rdf(Namespace("http://ldf.fi/warsa/prisoners/"),
                              Namespace("http://ldf.fi/schema/warsa/prisoners/"),
                              SCHEMA_NS.PrisonCamp)
        mapper.write_rdf(output_dir + "camps.ttl", output_dir + "camp_schema.ttl", fformat='turtle')

