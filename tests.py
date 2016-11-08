#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Tests for data conversion
"""
import datetime
import unittest

import converters

class TestConverters(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()