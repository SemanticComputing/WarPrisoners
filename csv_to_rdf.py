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
from rdflib import URIRef, Graph, Literal, Namespace

from converters import convert_person_name, convert_dates
from mapping import PRISONER_MAPPING

from csv2rdf import CSV2RDF
from namespaces import RDF, XSD, DC, FOAF, SKOS, DATA_NS, SCHEMA_NS, WARSA_NS


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
        self.errors = pd.DataFrame(columns=['nro', 'sarake', 'virhe', 'arvo'])

        logging.basicConfig(filename='prisoners.log',
                            filemode='a',
                            level=getattr(logging, loglevel),
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.log = logging.getLogger(__name__)

    def read_value_with_source(self, orig_value):
        """
        Read a value with source given in the end in parenthesis

        :param orig_value: string in format "value (source)"
        :return: value, sources, erroneous content
        """

        sourcematch = re.search(r'(.+) \(([^()]+)\)(.*)', orig_value)
        (value, sources, trash) = sourcematch.groups() if sourcematch else (orig_value, None, None)

        if sources:
            self.log.debug('Found sources: %s' % sources)
            sources = [s.strip() for s in sources.split(',')]

        if trash:
            self.log.warning('Found some content after sources, reverting to original: %s' % orig_value)
            value = orig_value

        return value.strip(), sources or [], trash or ''

    def read_semicolon_separated(self, orig_value: str):
        """
        Read semicolon separated values (with possible sources and date range)

        :param orig_value: string in format "source: value date1-date2", or just "value"
        :return: value, sources, date begin, date end, error
        """

        error = None
        if ': ' in orig_value:
            try:
                (sources, value) = orig_value.split(': ')
            except ValueError as err:
                self.log.error('Semicolon separated: %s caused error "%s"' % (orig_value, err))
                error = 'Unable to get source (multiple ": " in value)'
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
            self.log.debug('Found dates for value %s: %s - %s' % (value, date_begin, date_end))

        return value, sources or [], date_begin, date_end, error

    def map_row_to_rdf(self, entity_uri, row, prisoner_number=None):
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
        if lastname:
            row_rdf.add((entity_uri, FOAF.familyName, Literal(lastname)))
        if fullname:
            row_rdf.add((entity_uri, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'), Literal(fullname)))
        if original_name:
            row_rdf.add((entity_uri, SCHEMA_NS.original_name, Literal(original_name)))

        # Loop through the mapping dict and convert data to RDF
        for column_name in self.mapping:

            mapping = self.mapping[column_name]

            value = row[column_name]

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
                trash = None
                error = None
                original_value = value

                if separator == '/':
                    value, sources, trash = self.read_value_with_source(value)
                elif separator == ';':
                    value, sources, date_begin, date_end, error = self.read_semicolon_separated(value)

                if trash:
                    error = 'Extra content given after source: %s' % original_value
                if error:
                    error_row = pd.DataFrame(data=[[prisoner_number, column_name, error, original_value]],
                                             columns=self.errors.columns)
                    self.errors = self.errors.append(error_row)

                converter = mapping.get('converter')
                value = converter(value) if converter else value

                if value:
                    liter = Literal(value, datatype=XSD.date) if type(value) == datetime.date else Literal(value)
                    row_rdf.add((entity_uri, mapping['uri'], liter))

                    if mapping.get('reify_order_number'):
                        reification_uri = DATA_NS[reification_template.format(entity=entity_uri.split('/')[-1],
                                                                              prop=mapping['uri'].split('/')[-1],
                                                                              id=index,
                                                                              reason='order')]
                        row_rdf.add((reification_uri, RDF.subject, entity_uri))
                        row_rdf.add((reification_uri, RDF.predicate, mapping['uri']))
                        row_rdf.add((reification_uri, RDF.object, liter))
                        row_rdf.add((reification_uri, RDF.type, RDF.Statement))
                        row_rdf.add((reification_uri, SCHEMA_NS.order, Literal(index * 10)))

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

            if row_rdf:
                row_rdf.add((entity_uri, RDF.type, self.instance_class))
            else:
                # Don't create class instance if there is no data about it
                logging.debug('No data found for {uri}'.format(uri=entity_uri))

        return row_rdf

    def read_csv(self, csv_input):
        """
        Read in a CSV files using pandas.read_csv

        :param csv_input: CSV input (filename or buffer)
        """
        csv_data = pd.read_csv(csv_input, encoding='UTF-8', index_col=False, sep=',', quotechar='"',
                               # parse_dates=[1], infer_datetime_format=True, dayfirst=True,
                               na_values=[' '],
                               converters={
                                   'ammatti': lambda x: x.lower(),
                                   0: lambda x: int(x) if x and x.isnumeric() else -1
                               })

        self.table = csv_data.fillna('').applymap(lambda x: x.strip() if type(x) == str else x)
        logging.info('Read {num} rows from CSV'.format(num=len(self.table)))
        self.table.rename(columns={'Unnamed: 0': 'nro'}, inplace=True)
        self.table = self.table[self.table.nro >= 0]  # Take out persons which don't have a number
        logging.info('After pruning rows without proper index, {num} rows remaining'.format(num=len(self.table)))
        self.log.info('Data read from CSV %s' % csv_input)

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
        self.data.bind("dct", 'http://purl.org/dc/terms/')

        self.schema.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
        self.schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.schema.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.schema.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.schema.bind("bioc", 'http://ldf.fi/schema/bioc/')

        data = self.data.serialize(format="turtle", destination=destination_data)
        schema = self.schema.serialize(format="turtle", destination=destination_schema)
        self.log.info('Data serialized to %s' % destination_data)
        self.log.info('Schema serialized to %s' % destination_schema)

        return data, schema  # Return for testing purposes

    def process_rows(self):
        """
        Loop through CSV rows and convert them to RDF
        """
        for index in self.table.index:
            prisoner_number = self.table.ix[index][0]
            prisoner_uri = DATA_NS['prisoner_' + str(prisoner_number)]
            row_rdf = self.map_row_to_rdf(prisoner_uri, self.table.ix[index][1:], prisoner_number=prisoner_number)
            if row_rdf:
                self.data += row_rdf

        for prop in PRISONER_MAPPING.values():
            self.schema.add((prop['uri'], RDF.type, RDF.Property))
            if 'name_fi' in prop:
                self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
            if 'name_en' in prop:
                self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_en'], lang='en')))

        self.errors.to_csv('errors.csv', ',', index=False)


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Process war prisoners CSV", fromfile_prefix_chars='@')

    argparser.add_argument("mode", help="CSV conversion mode", default="PRISONERS",
                           choices=["PRISONERS", "CAMPS", "HOSPITALS"])
    argparser.add_argument("input", help="Input CSV file")
    argparser.add_argument("--outdata", help="Output file to serialize RDF dataset to (.ttl)", default=None)
    argparser.add_argument("--outschema", help="Output file to serialize RDF schema to (.ttl)", default=None)
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

    args = argparser.parse_args()

    if args.mode == "PRISONERS":
        mapper = RDFMapper(PRISONER_MAPPING, WARSA_NS.PrisonerRecord, loglevel=args.loglevel.upper())
        mapper.read_csv(args.input)

        mapper.process_rows()

        mapper.serialize(args.outdata, args.outschema)

    elif args.mode == "CAMPS":
        mapper = CSV2RDF()
        mapper.read_csv(args.input, sep='\t')
        mapper.convert_to_rdf(Namespace("http://ldf.fi/warsa/prisoners/"),
                              Namespace("http://ldf.fi/schema/warsa/prisoners/"),
                              WARSA_NS.PrisonCamp)
        mapper.write_rdf(args.outdata, args.outschema, fformat='turtle')

    elif args.mode == "HOSPITALS":
        mapper = CSV2RDF()
        mapper.read_csv(args.input, sep='\t')
        mapper.convert_to_rdf(Namespace("http://ldf.fi/warsa/prisoners/"),
                              Namespace("http://ldf.fi/schema/warsa/prisoners/"),
                              WARSA_NS.Hospital)
        mapper.write_rdf(args.outdata, args.outschema, fformat='turtle')
