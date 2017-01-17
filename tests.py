#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Tests for data conversion
"""
import argparse
import datetime
from unittest import mock, TestCase, main

import converters


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

    @mock.patch('argparse.ArgumentParser.parse_args',
                return_value=argparse.Namespace(input='test_data.csv', output='foo', loglevel='WARNING'))
    @mock.patch('rdflib.Graph.serialize', return_value=None)
    def test_command(self, mock_args, mock_args2):
        import csv_to_rdf


if __name__ == '__main__':
    main()
