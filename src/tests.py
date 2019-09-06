#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Tests for data conversion

To run all tests (including doctests) you can use for example nose: nosetests --with-doctest
"""
import datetime
import io
import unittest
from pprint import pprint, pformat

from rdflib import Graph, URIRef, Literal, RDF
from rdflib.compare import isomorphic, graph_diff

import converters
from csv_to_rdf import RDFMapper, get_triple_reifications
from linker import _generate_prisoners_dict
from mapping import PRISONER_MAPPING
from namespaces import DATA_NS, DCT, SCHEMA_WARSA, SCHEMA_POW, RANKS_NS, SKOS, MUNICIPALITIES, SCHEMA_ACTORS, BIOC, ACTORS
from prune_nonpublic import prune_persons


class TestConverters(unittest.TestCase):
    # TODO: Test errors also

    def test_convert_dates(self):
        self.assertEqual(converters.convert_dates('24.12.2016'), datetime.date(2016, 12, 24))
        self.assertEqual(converters.convert_dates('24/12/2016'), datetime.date(2016, 12, 24))

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
        instance_class = URIRef(SCHEMA_WARSA.PrisonerRecord)

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
        p = SCHEMA_POW.municipality_of_residence_literal
        o = Literal('Hämeenlinna')

        ref = get_triple_reifications(g, (s, p, o))
        ref_subs = set(ref.subjects())
        self.assertEquals(len(ref_subs), 1)

        ref_sub = ref_subs.pop()
        source = g.value(ref_sub, DCT.source)
        self.assertEquals(source, Literal('mikrofilmi'))

    def test_prune_persons(self):
        g = Graph().parse('test_data/prisoners.ttl', format='turtle')
        g2 = prune_persons(g, "http://ldf.fi/warsa/sparql")

        diffs = graph_diff(g, g2)

        print('In new:')
        pprint([d for d in diffs[1]])

        print('In old:')
        pprint([d for d in diffs[2]])

        self.assertEqual(sorted(g.subjects()), sorted(g2.subjects()))

    def test_get_mapping(self):
        mapper = RDFMapper({'column1': {}}, '')
        self.assertEquals(mapper.get_mapping('column1 (kesken)'), {})


class TestPersonLinking(unittest.TestCase):
    maxDiff = None

    ranks = Graph()
    ranks.add((RANKS_NS.Korpraali, SKOS.prefLabel, Literal('Korpraali', lang='fi')))
    ranks.add((RANKS_NS.Kapteeni, SKOS.prefLabel, Literal('Kapteeni', lang='fi')))
    ranks.add((RANKS_NS.Korpraali, SCHEMA_ACTORS.level, Literal(3)))
    ranks.add((RANKS_NS.Kapteeni, SCHEMA_ACTORS.level, Literal(11)))

    def test_generate_prisoners_dict(self):
        expected = {
            'foo': {'activity_end': '1941-12-23',
                    'birth_begin': '1906-12-23',
                    'birth_end': '1906-12-23',
                    'birth_place': [URIRef('http://ldf.fi/warsa/places/municipalities/k123')],
                    'death_begin': '1941-12-23',
                    'death_end': '1941-12-23',
                    'family': 'Heino',
                    'given': 'Eino Ilmari',
                    'occupation': None,
                    'person': None,
                    'death_place': None,
                    'rank': ['http://ldf.fi/schema/warsa/actors/ranks/Korpraali'],
                    'rank_level': 3,
                    'unit': None}
        }

        g = Graph()
        p = URIRef('foo')
        g.add((p, RDF.type, SCHEMA_WARSA.PrisonerRecord))
        g.add((p, SCHEMA_POW.rank, RANKS_NS.Korpraali))
        g.add((p, SCHEMA_WARSA.given_names, Literal("Eino Ilmari")))
        g.add((p, SCHEMA_WARSA.family_name, Literal("Heino")))
        g.add((p, SCHEMA_WARSA.municipality_of_birth, MUNICIPALITIES.k123))
        g.add((p, SCHEMA_WARSA.date_of_birth, Literal(datetime.date(1906, 12, 23))))
        g.add((p, SCHEMA_POW.date_of_death, Literal(datetime.date(1941, 12, 23))))
        pd = _generate_prisoners_dict(g, self.ranks)

        self.assertEqual(expected, pd, pformat(pd))

    def test_generate_prisoners_dict_2(self):
        expected = {
            'foo': {'activity_end': '1943-02-03',
                    'birth_begin': '1906-12-23',
                    'birth_end': '1916-06-03',
                    'birth_place': [URIRef('http://ldf.fi/warsa/places/municipalities/k123'),
                                    URIRef('http://ldf.fi/warsa/places/municipalities/k234')],
                    'death_begin': '1941-12-23',
                    'death_end': '1943-02-03',
                    'death_place': [URIRef('http://ldf.fi/warsa/places/municipalities/k234')],
                    'family': 'Heino Kalmari',
                    'given': 'Eino Ilmari',
                    'occupation': [URIRef('http://ldf.fi/warsa/occupations/sekatyomies'),
                                   URIRef('http://ldf.fi/warsa/occupations/tyomies')],
                    'person': None,
                    'rank': ['http://ldf.fi/schema/warsa/actors/ranks/Kapteeni',
                             'http://ldf.fi/schema/warsa/actors/ranks/Korpraali'],
                    'rank_level': 11,
                    'unit': [ACTORS.actor_12839]}
        }

        g = Graph()
        p = URIRef('foo')
        g.add((p, RDF.type, SCHEMA_WARSA.PrisonerRecord))
        g.add((p, SCHEMA_POW.rank, RANKS_NS.Korpraali))
        g.add((p, SCHEMA_POW.rank, RANKS_NS.Kapteeni))
        g.add((p, SCHEMA_WARSA.given_names, Literal("Eino Ilmari")))
        g.add((p, SCHEMA_WARSA.family_name, Literal("Heino (ent. Kalmari)")))
        g.add((p, SCHEMA_WARSA.municipality_of_birth, MUNICIPALITIES.k123))
        g.add((p, SCHEMA_WARSA.municipality_of_birth, MUNICIPALITIES.k234))
        g.add((p, SCHEMA_WARSA.date_of_birth, Literal(datetime.date(1906, 12, 23))))
        g.add((p, SCHEMA_WARSA.date_of_birth, Literal(datetime.date(1916, 6, 3))))
        g.add((p, SCHEMA_POW.date_of_death, Literal(datetime.date(1941, 12, 23))))
        g.add((p, SCHEMA_POW.date_of_death, Literal(datetime.date(1943, 2, 3))))
        g.add((p, SCHEMA_WARSA.municipality_of_death, MUNICIPALITIES.k234))
        g.add((p, BIOC.has_occupation, URIRef('http://ldf.fi/warsa/occupations/sekatyomies')))
        g.add((p, BIOC.has_occupation, URIRef('http://ldf.fi/warsa/occupations/tyomies')))
        g.add((p, SCHEMA_POW.unit, ACTORS.actor_12839))
        pd = _generate_prisoners_dict(g, self.ranks)

        self.assertEqual(expected, pd, pformat(pd))


if __name__ == '__main__':
    unittest.main()
