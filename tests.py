#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Tests for data conversion
"""
import argparse
import datetime
import io
from unittest import mock, TestCase, main

from rdflib import Graph
from rdflib import URIRef

from csv_to_rdf import RDFMapper
import converters
from mapping import PRISONER_MAPPING, RDF


class TestConverters(TestCase):

    def test_convert_int(self):
        self.assertIsInstance(converters.convert_int('1234'), int)

        self.assertEqual(converters.convert_int('5'), 5)
        self.assertEqual(converters.convert_int('0'), 0)
        self.assertEqual(converters.convert_int('-5'), -5)

        self.assertEqual(converters.convert_int(''), '')
        self.assertEqual(converters.convert_int('foobar'), 'foobar')

    def test_convert_dates(self):
        self.assertEqual(converters.convert_dates('24.12.2016'), datetime.date(2016, 12, 24))
        self.assertEqual(converters.convert_dates('24/12/2016'), datetime.date(2016, 12, 24))

        self.assertEqual(converters.convert_dates('xx.xx.xxxx'), 'xx.xx.xxxx')

    def test_convert_person_name(self):
        self.assertEqual(converters.convert_person_name('Virtanen Matti Akseli'),
                         ('Matti Akseli', 'Virtanen', 'Virtanen, Matti Akseli'))

        self.assertEqual(converters.convert_person_name('Huurre ent. Hildén Aapo Antero'),
                         ('Aapo Antero', 'Huurre (ent. Hildén)', 'Huurre (ent. Hildén), Aapo Antero'))

        self.assertEqual(converters.convert_person_name('Kulento ent. Kulakov Nikolai (Niilo)'),
                         ('Nikolai (Niilo)', 'Kulento (ent. Kulakov)', 'Kulento (ent. Kulakov), Nikolai (Niilo)'))

        self.assertEqual(converters.convert_person_name('Ahjo ent. Germanoff Juho ent. Ivan'),
                         ('Juho Ent. Ivan', 'Ahjo (ent. Germanoff)', 'Ahjo (ent. Germanoff), Juho Ent. Ivan'))


class TestCSV2RDF(TestCase):

    def test_read_csv(self):
        test_csv = '''col1  col2    col3
        1   2   3
        4   5   6
        7   8   9
        '''

        mapper = RDFMapper({}, '')
        mapper.read_csv(io.StringIO(test_csv))
        assert len(mapper.table) == 3

    def test_read_csv2(self):
        mapper = RDFMapper({}, '')
        mapper.read_csv('test_data.csv')
        assert len(mapper.table) == 1

    def test_mapping(self):
        instance_class = URIRef('http://example.com/Class')

        mapper = RDFMapper(PRISONER_MAPPING, instance_class)
        mapper.read_csv('test_data.csv')
        mapper.process_rows()
        rdf_data, schema = mapper.serialize(None, None)
        g = Graph().parse(io.StringIO(rdf_data.decode("utf-8")), format='turtle')

        types = list(g.objects(None, RDF.type))

        # print(rdf_data.decode("utf-8"))

        assert len(types) == 1
        assert types[0] == instance_class
        assert len(g) == 47  # 43 columns with data + firstname + lastname + prefLabel + rdf:type


if __name__ == '__main__':
    main()
