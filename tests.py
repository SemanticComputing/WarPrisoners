#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Tests for data conversion
"""
import datetime
import io
from collections import defaultdict
import unittest

from rdflib import Graph, RDF, URIRef
from rdflib import Literal
from rdflib import XSD

import converters
from csv_to_rdf import RDFMapper
from mapping import PRISONER_MAPPING, DATA_NS, DC


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


class TestCSV2RDF(unittest.TestCase):

    def test_read_value_with_source(self):
        mapper = RDFMapper({}, '')

        assert mapper.read_value_with_source('Some text') == ('Some text', [])
        assert mapper.read_value_with_source('Some text (source A)') == ('Some text', ['source A'])
        assert mapper.read_value_with_source('Some text (source A, source B)') == ('Some text',
                                                                                   ['source A', 'source B'])

    def test_read_semicolon_separated(self):
        mapper = RDFMapper({}, '')

        assert mapper.read_semicolon_separated('Some text') == ('Some text', [])
        assert mapper.read_semicolon_separated('Source: Value') == ('Value', ['Source'])
        assert mapper.read_semicolon_separated('Source1, Source2: Value') == ('Value', ['Source1', 'Source2'])
        assert mapper.read_semicolon_separated('http://example.com/') == ('http://example.com/', [])

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
        assert len(mapper.table) == 2

    def test_mapping(self):
        instance_class = URIRef('http://example.com/Class')

        mapper = RDFMapper(PRISONER_MAPPING, instance_class)
        mapper.read_csv('test_data.csv')
        mapper.process_rows()
        rdf_data, schema = mapper.serialize(None, None)
        g = Graph().parse(io.StringIO(rdf_data.decode("utf-8")), format='turtle')

        # print(rdf_data.decode("utf-8"))

        instances = list(g.subjects(RDF.type, instance_class))
        assert len(instances) == 2

        p0 = list(g[DATA_NS.prisoner_0::])
        print(len(p0))
        assert len(p0) == 50
        # 43 columns with data + firstname + lastname + prefLabel + rdf:type + 3 columns with two values

    def test_mapping_field_contents(self):
        instance_class = URIRef('http://example.com/Class')

        mapper = RDFMapper(PRISONER_MAPPING, instance_class)
        mapper.read_csv('test_data.csv')
        mapper.process_rows()
        rdf_data, schema = mapper.serialize(None, None)
        g = Graph().parse(io.StringIO(rdf_data.decode("utf-8")), format='turtle')

        p1 = list(g[DATA_NS.prisoner_1::])
        assert len(p1) > 20

        p1_dict = defaultdict(list)
        for k, v in p1:
            p1_dict[k].append(v)

        # Birth date

        birth_dates = p1_dict[PRISONER_MAPPING['syntymäaika']['uri']]
        assert len(birth_dates) == 2

        assert birth_dates[0].datatype == URIRef('http://www.w3.org/2001/XMLSchema#date')
        assert birth_dates[1].datatype == URIRef('http://www.w3.org/2001/XMLSchema#date')

        # No reifications
        assert len(list(g[:RDF.object:birth_dates[0]])) == 0
        assert len(list(g[:RDF.object:birth_dates[1]])) == 0

        # Place of domicile

        places = p1_dict[PRISONER_MAPPING['asuinpaikka']['uri']]
        assert len(places) == 2

        assert places[0].datatype is None
        assert places[1].datatype is None

        # Some reifications
        assert len(list(g[:RDF.object:Literal('Viipuri')])) == 0
        assert len(list(g[:RDF.object:Literal('Hämeenlinna')])) == 1

        # Death date

        death_dates = p1_dict[PRISONER_MAPPING['kuollut']['uri']]
        assert len(death_dates) == 3

        assert death_dates[0].datatype == URIRef('http://www.w3.org/2001/XMLSchema#date')
        assert death_dates[1].datatype == URIRef('http://www.w3.org/2001/XMLSchema#date')
        assert death_dates[2].datatype == URIRef('http://www.w3.org/2001/XMLSchema#date')

        # Some reifications
        r0 = g.value(None, RDF.object, Literal('1943-02-02', datatype=XSD.date))

        assert g.value(r0, RDF.type, None) == RDF.Statement
        assert g.value(r0, RDF.predicate, None) == PRISONER_MAPPING['kuollut']['uri']
        assert g.value(r0, DC.source, None) == Literal('Karaganda')

        r1 = g.value(None, RDF.object, Literal('1943-03-02', datatype=XSD.date))

        assert g.value(r1, DC.source, None) == Literal('mikrofilmi')

        r2 = g.value(None, RDF.object, Literal('1943-03-13', datatype=XSD.date))
        assert r2 is None

        r_other = g.value(None, DC.source, Literal('KA-internet'))
        assert g.value(r_other, RDF.object, None) == Literal('kadonnut, julistettu virallisesti kuolleeksi.')


if __name__ == '__main__':
    unittest.main()
