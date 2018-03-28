#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Tests for data conversion

To run all tests (including doctests) you can use for example nose: nosetests --with-doctest
"""
import datetime
import io
import unittest
from pprint import pprint

from rdflib import Graph, URIRef, Literal
from rdflib.compare import isomorphic, graph_diff

import converters
from csv_to_rdf import RDFMapper, get_triple_reifications
from mapping import PRISONER_MAPPING
from namespaces import DATA_NS, DC, WARSA_NS, SCHEMA_NS
from prune_nonpublic import prune_persons


class TestConverters(unittest.TestCase):
    # TODO: Test errors also

    def test_convert_dates(self):
        self.assertEqual(converters.convert_dates('24.12.2016'), datetime.date(2016, 12, 24))
        self.assertEqual(converters.convert_dates('12/24/2016'), datetime.date(2016, 12, 24))

        self.assertEqual(converters.convert_dates('xx.xx.xxxx'), 'xx.xx.xxxx')
        self.assertEqual(converters.convert_dates('xx.09.2016'), 'xx.09.2016')

    def test_convert_person_name(self):
        self.assertEqual(converters.convert_person_name('Virtanen Matti Akseli'),
                         ('Matti Akseli', 'Virtanen', 'Virtanen, Matti Akseli'))

        self.assertEqual(converters.convert_person_name('Huurre ent. Hildén Aapo Antero'),
                         ('Aapo Antero', 'Huurre (ent. Hildén)', 'Huurre (ent. Hildén), Aapo Antero'))

        self.assertEqual(converters.convert_person_name('Kulento ent. Kulakov Nikolai (Niilo)'),
                         ('Nikolai (Niilo)', 'Kulento (ent. Kulakov)', 'Kulento (ent. Kulakov), Nikolai (Niilo)'))

        self.assertEqual(converters.convert_person_name('Ahjo ent. Germanoff Juho ent. Ivan'),
                         ('Juho Ent. Ivan', 'Ahjo (ent. Germanoff)', 'Ahjo (ent. Germanoff), Juho Ent. Ivan'))

    def test_strip_dash(self):
        self.assertEqual(converters.strip_dash('-'), '')
        self.assertEqual(converters.strip_dash('Foo-Bar'), 'Foo-Bar')


class TestRDFMapper(unittest.TestCase):
    def test_read_value_with_source(self):
        mapper = RDFMapper({}, '')

        self.assertEqual(mapper.read_value_with_source('Some text'), ('Some text', [], ''))
        self.assertEqual(mapper.read_value_with_source('Some text (source A)'), ('Some text', ['source A'], ''))
        self.assertEqual(mapper.read_value_with_source('Some text (source A, source B)'), ('Some text',
                                                                                           ['source A, source B'], ''))

    def test_read_semicolon_separated(self):
        mapper = RDFMapper({}, '')

        self.assertEquals(mapper.read_semicolon_separated('Some text'), ('Some text', [], None, None, []))
        self.assertEquals(mapper.read_semicolon_separated('Source: Value'), ('Value', ['Source'], None, None, []))
        self.assertEquals(mapper.read_semicolon_separated('Source1, Source2: Value'),
                          ('Value', ['Source1, Source2'], None, None, []))
        self.assertEquals(mapper.read_semicolon_separated('http://example.com/'),
                          ('http://example.com/', [], None, None, []))

        self.assertEquals(mapper.read_semicolon_separated('54 13.10.1942-xx.11.1942'),
                          ('54', [], datetime.date(1942, 10, 13), 'xx.11.1942', []))

    def test_read_csv_simple_2(self):
        mapper = RDFMapper({}, '')
        mapper.read_csv('test_data/prisoners.csv')
        assert len(mapper.table) == 2

    def test_mapping_field_contents(self):
        instance_class = URIRef(WARSA_NS.PrisonerRecord)

        mapper = RDFMapper(PRISONER_MAPPING, instance_class)
        mapper.read_csv('test_data/prisoners.csv')
        mapper.preprocess_prisoners_data()
        mapper.process_rows()
        rdf_data, schema = mapper.serialize(None, None)
        g = Graph().parse(io.StringIO(rdf_data.decode("utf-8")), format='turtle')

        # g.serialize('test_data/prisoners.ttl', format="turtle")  # Decomment to update file, and verify it by hand
        g2 = Graph().parse('test_data/prisoners.ttl', format='turtle')

        diffs = graph_diff(g, g2)

        print('In new:')
        pprint([d for d in diffs[1]])

        print('In old:')
        pprint([d for d in diffs[2]])

        assert isomorphic(g, g2)  # Isomorphic graph comparison

    def test_get_triple_reifications(self):
        g = Graph().parse('test_data/prisoners.ttl', format='turtle')

        s = DATA_NS.prisoner_2
        p = SCHEMA_NS.residence_place
        o = Literal('Hämeenlinna')

        ref = get_triple_reifications(g, (s, p, o))
        ref_subs = set(ref.subjects())
        self.assertEquals(len(ref_subs), 1)

        ref_sub = ref_subs.pop()
        source = g.value(ref_sub, DC.source)
        self.assertEquals(source, Literal('mikrofilmi'))

    def test_prune_persons(self):
        g = Graph().parse('test_data/prisoners.ttl', format='turtle')
        public, hidden = prune_persons(g)
        print(len(public))
        print(len(hidden))

        g2 = public + hidden

        diffs = graph_diff(g, g2)

        print('In new:')
        pprint([d for d in diffs[1]])

        print('In old:')
        pprint([d for d in diffs[2]])

        assert isomorphic(g, g2)

    def test_get_mapping(self):
        mapper = RDFMapper({'column1': {}}, '')
        self.assertEquals(mapper.get_mapping('column1 (kesken)'), {})


if __name__ == '__main__':
    unittest.main()
