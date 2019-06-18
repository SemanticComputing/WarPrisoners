#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""
import json

import numpy
from datetime import date
from itertools import chain

import argparse
import logging
import random
import re
import time

from arpa_linker.arpa import ArpaMimic, Arpa
from rdflib import Graph, URIRef, RDF, Literal
from rdflib.exceptions import UniquenessError
from rdflib.util import guess_format
import rdf_dm as r

from namespaces import SCHEMA_POW, BIOC, SCHEMA_WARSA, bind_namespaces, SCHEMA_ACTORS, SKOS, RANKS_NS, MUNICIPALITIES
from warsa_linkers.municipalities import link_to_pnr, link_warsa_municipality
from warsa_linkers.occupations import link_occupations
from warsa_linkers.person_record_linkage import link_persons, intersection_comparator, activity_comparator, \
    get_date_value, read_person_links
from warsa_linkers.ranks import link_ranks
import warsa_linkers.person_record_linkage

log = logging.getLogger(__name__)

warsa_linkers.person_record_linkage.log = log

# TODO: Write some tests using responses


def _preprocess(literal, prisoner, subgraph):
    """Default preprocess implementation for link function"""
    return str(literal).strip()


def link(graph, arpa, source_prop, target_graph, target_prop, preprocess=_preprocess, validator=None):
    """
    Link entities with ARPA based on parameters

    :return: target_graph with found links
    """
    prop_str = str(source_prop).split('/')[-1]  # Used for logging

    for (prisoner, value_literal) in list(graph[:source_prop:]):
        value = preprocess(value_literal, prisoner, graph)

        log.debug('Finding links for %s (originally %s)' % (value, value_literal))

        if value:
            arpa_result = arpa.query(value)
            if arpa_result:
                res = arpa_result[0]['id']

                if validator:
                    res = validator.validate(arpa_result, value_literal, prisoner)
                    if not res:
                        log.info('Match {res} failed validation for {val}, skipping it'.
                                 format(res=res, val=value_literal))
                        continue

                log.info('Accepted a match for property {ps} with original value {val} : {res}'.
                         format(ps=prop_str, val=value_literal, res=res))

                target_graph.add((prisoner, target_prop, URIRef(res)))
            else:
                log.warning('No match found for %s: %s' % (prop_str, value))

    return target_graph


def link_camps(graph, endpoint):
    """Link PoW camps."""

    value_mapping = {
        'Siestarjoki': "Siestarjoki, ven. Sestroretsk",
        'Karhumäki': "Karhumäki, evakuointipiste",
        'Sorokka': 'Sorokka ven. Belomorsk',
    }

    def preprocess(literal, prisoner, subgraph):
        literal = str(literal).strip().replace('"', '\\"')

        log.debug(f'Preprocessing camp for linking, {literal} : {value_mapping.get(literal, literal)}')
        return value_mapping.get(literal, literal)

    query = "PREFIX ps:<http://ldf.fi/schema/warsa/prisoners/>" + \
            "SELECT * {" + \
            "  GRAPH <http://ldf.fi/warsa/prisoners> {" + \
            "    VALUES ?place { \"<VALUES>\" }" + \
            "    ?id ps:camp_id|ps:captivity_location ?place . " + \
            "  }" + \
            "}"

    arpa = ArpaMimic(query, url=endpoint, retries=3, wait_between_tries=3)

    return link(graph, arpa, SCHEMA_POW.location_literal, Graph(), SCHEMA_POW.location, preprocess=preprocess)


def _generate_prisoners_dict(graph: Graph, ranks: Graph):
    """
    Generate a persons dict from POW records.
    """

    # TODO: municipality_of_death

    prisoners = {}
    for person in graph[:RDF.type:SCHEMA_WARSA.PrisonerRecord]:
        rank_uris = list(graph.objects(person, SCHEMA_POW.rank))

        given = str(graph.value(person, SCHEMA_WARSA.given_names, any=False))
        family = str(graph.value(person, SCHEMA_WARSA.family_name, any=False))
        rank = [str(r) for r in rank_uris if r] or None
        birth_places = graph.objects(person, SCHEMA_POW.municipality_of_birth)
        units = graph.objects(person, SCHEMA_POW.unit)
        occupations = graph.objects(person, BIOC.has_occupation)

        births = [get_date_value(bd) for bd in graph.objects(person, SCHEMA_POW.date_of_birth)]
        deaths = [get_date_value(dd) for dd in graph.objects(person, SCHEMA_POW.date_of_death)]
        birth_begin = min([d for d in births if d] or [None])
        birth_end = max([d for d in births if d] or [None])
        death_begin = min([d for d in deaths if d] or [None])
        death_end = max([d for d in deaths if d] or [None])

        rank_levels = []
        try:
            for rank_uri in rank_uris:
                rank_levels.append(int(ranks.value(rank_uri, SCHEMA_ACTORS.level, any=False)))
        except (TypeError, UniquenessError):
            pass

        prisoner = {'person': None,
                    'rank': sorted(rank) if rank else None,
                    'rank_level': max(rank_levels or [None]),
                    'given': given,
                    'family': re.sub(r'\(ent\.\s*(.+)\)', r'\1', family),
                    'birth_place': sorted(birth_places) if birth_places else None,
                    'birth_begin': birth_begin,
                    'birth_end': birth_end,
                    'death_begin': death_begin,
                    'death_end': death_end,
                    'activity_end': death_end,
                    'unit': sorted(units) or None,
                    'occupation': sorted(occupations) or None
                    }
        prisoners[str(person)] = prisoner

        log.debug('Prisoner: {}'.format(prisoner))

    return prisoners


def link_prisoners(input_graph, endpoint):
    data_fields = [
        {'field': 'given', 'type': 'String'},
        {'field': 'family', 'type': 'String'},
        {'field': 'birth_place', 'type': 'Custom', 'comparator': intersection_comparator, 'has missing': True},
        {'field': 'birth_begin', 'type': 'DateTime', 'has missing': True, 'fuzzy': False},
        {'field': 'birth_end', 'type': 'DateTime', 'has missing': True, 'fuzzy': False},
        {'field': 'death_begin', 'type': 'DateTime', 'has missing': True, 'fuzzy': False},
        {'field': 'death_end', 'type': 'DateTime', 'has missing': True, 'fuzzy': False},
        # TODO: municipality_of_death
        {'field': 'activity_end', 'type': 'Custom', 'comparator': activity_comparator, 'has missing': True},
        {'field': 'rank', 'type': 'Custom', 'comparator': intersection_comparator, 'has missing': True},
        {'field': 'rank_level', 'type': 'Price', 'has missing': True},
        {'field': 'unit', 'type': 'Custom', 'comparator': intersection_comparator, 'has missing': True},
    ]

    ranks = r.read_graph_from_sparql(endpoint, "http://ldf.fi/warsa/ranks")

    random.seed(42)  # Initialize randomization to create deterministic results
    numpy.random.seed(42)

    training_links = read_person_links('data/person_links.json')

    return link_persons(endpoint, _generate_prisoners_dict(input_graph, ranks), data_fields, training_links,
                        sample_size=500000,
                        threshold_ratio=0.8
                        )


def add_link(graph: Graph, munic_mapping: dict, sourceprop: URIRef, targetprop: URIRef):
    literals = graph.subject_objects(sourceprop)
    munic_links = Graph()
    for sub, obj in literals:
        try:
            munic_links.add((sub, targetprop, munic_mapping[str(obj)]))
        except KeyError:
            pass

    return munic_links


def link_municipalities(g: Graph, warsa_endpoint: str, arpa_endpoint: str):
    """
    Link to Warsa municipalities.
    """

    warsa_munics = r.helpers.read_graph_from_sparql(warsa_endpoint,
                                                    graph_name='http://ldf.fi/warsa/places/municipalities')

    log.info('Using Warsa municipalities with {n} triples'.format(n=len(warsa_munics)))

    pnr_arpa = Arpa(arpa_endpoint)
    pnr_links = link_to_pnr(g, SCHEMA_POW.municipality_of_death,
                            SCHEMA_POW.municipality_of_death_literal, pnr_arpa)['graph']

    war_munics = set(g.objects(None, SCHEMA_POW.municipality_of_birth_literal)) | \
                 set(g.objects(None, SCHEMA_POW.municipality_of_domicile_literal)) | \
                 set(g.objects(None, SCHEMA_POW.municipality_of_residence_literal)) | \
                 set(g.objects(None, SCHEMA_POW.municipality_of_capture_literal))

    war_munic_mapping = {}
    war_munic_links = Graph()

    for munic_literal in war_munics:
        warsa_match = link_warsa_municipality(warsa_munics, [str(munic_literal)])
        if warsa_match:
            war_munic_mapping[str(munic_literal)] = warsa_match
        else:
            log.warning('No warsa link found for municipality {}'.format(munic_literal))

    for source, target in [(SCHEMA_POW.municipality_of_birth_literal, SCHEMA_POW.municipality_of_birth),
                           (SCHEMA_POW.municipality_of_domicile_literal, SCHEMA_POW.municipality_of_domicile),
                           (SCHEMA_POW.municipality_of_residence_literal, SCHEMA_POW.municipality_of_residence),
                           (SCHEMA_POW.municipality_of_capture_literal, SCHEMA_POW.municipality_of_capture)]:
        war_munic_links += add_link(g, war_munic_mapping, source, target)

    return war_munic_links + pnr_links


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="War prisoner linking tasks", fromfile_prefix_chars='@')

    argparser.add_argument("task", help="Linking task to perform",
                           choices=["camps", "occupations", "municipalities", "persons", "ranks"])
    argparser.add_argument("input", help="Input RDF file")
    argparser.add_argument("output", help="Output file location")
    argparser.add_argument("--logfile", default='tasks.log', help="Logfile")
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    argparser.add_argument("--endpoint", default='http://localhost:3030/warsa/sparql', help="SPARQL Endpoint")
    argparser.add_argument("--arpa", type=str, help="ARPA instance URL for linking")

    args = argparser.parse_args()

    log_handler = logging.FileHandler(args.logfile)
    log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    log.addHandler(log_handler)
    log.setLevel(args.loglevel)

    input_graph = Graph()
    input_graph.parse(args.input, format=guess_format(args.input))

    if args.task == 'camps':
        log.info('Linking camps and hospitals')
        bind_namespaces(link_camps(input_graph, args.endpoint)).serialize(args.output, format=guess_format(args.output))

    elif args.task == 'municipalities':
        log.info('Linking municipalities')
        link_municipalities(input_graph, args.endpoint, args.arpa)

    elif args.task == 'occupations':
        log.info('Linking occupations')
        bind_namespaces(link_occupations(input_graph, args.endpoint, SCHEMA_POW.occupation_literal, BIOC.has_occupation,
                                         SCHEMA_WARSA.PrisonerRecord)).serialize(args.output, format=guess_format(args.output))

    elif args.task == 'persons':
        log.info('Linking persons')
        bind_namespaces(link_prisoners(input_graph, args.endpoint)).serialize(args.output, format=guess_format(args.output))

    elif args.task == 'ranks':
        log.info('Linking ranks')
        bind_namespaces(link_ranks(input_graph, args.endpoint, SCHEMA_POW.rank_literal, SCHEMA_POW.rank,
                                   SCHEMA_WARSA.PrisonerRecord)).serialize(args.output, format=guess_format(args.output))

