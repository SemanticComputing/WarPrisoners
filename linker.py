#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""

import argparse
import logging
import re

import itertools
from pprint import pprint

import copy

from fuzzywuzzy import fuzz
from rdflib.compare import graph_diff

from arpa_linker.arpa import ArpaMimic, arpafy, Arpa
from rdflib import Graph
from rdflib import URIRef
from rdflib.util import guess_format

from namespaces import *

# TODO: Write some tests using responses


def _preprocess(literal, prisoner, subgraph):
    """Default preprocess implementation for link function"""
    return str(literal).strip()


def link(graph, arpa, prop, preprocess=_preprocess, validator=None):
    """
    Link entities based on parameters

    :return:
    """
    prop_str = str(prop).split('/')[-1]  # Used for logging

    # linked = arpafy(copy.deepcopy(graph), SCHEMA_NS.temp, arpa, SCHEMA_NS.rank, preprocessor=preprocess, progress=True)['graph']
    #
    # new_triples = graph_diff(graph, linked)[2]

    for (prisoner, value_literal) in list(graph[:prop:]):
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

                # Update property to found value
                graph.remove((prisoner, prop, value_literal))
                graph.add((prisoner, prop, URIRef(res)))

                # TODO: Update reifications
            else:
                log.warning('No match found for %s: %s' % (prop_str, value))

    return graph


def link_ranks(graph, endpoint):
    """
    Link military ranks in graph.

    :param graph: Data in RDFLib Graph object 
    :param endpoint: Endpoint to query military ranks from
    :param prop: Property used to give military rank (used for both source and target) 
    :return: RDFLib Graph with updated links
    """
    def preprocess(literal, prisoner, subgraph):
        value = re.sub(r'[/\-]', ' ', str(literal)).strip()
        return mapping[value] if value in mapping else value

    mapping = {'kaart': 'stm',
               'aliluutn': 'aliluutnantti'}

    query = "PREFIX text: <http://jena.apache.org/text#> " +\
            "SELECT * { ?id a <http://ldf.fi/warsa/actors/ranks/Rank> . " +\
            "?id text:query \"<VALUES>\" . " +\
            "}"

    arpa = ArpaMimic(query, url=endpoint, retries=3, wait_between_tries=3)

    return link(graph, arpa, SCHEMA_NS.rank, preprocess=preprocess)


def _create_unit_abbreviations(text, *args):
    """
    Preprocess military unit abbreviation strings for all possible combinations

    :param text: Military unit abbreviation
    :return: List containing all possible abbrevations

    >>> _create_unit_abbreviations('3./JR 1')
    '3./JR 1 # 3./JR. 1. # 3./JR.1. # 3./JR1 # 3/JR 1 # 3/JR. 1. # 3/JR.1. # 3/JR1 # JR 1 # JR. 1. # JR.1. # JR1'
    >>> _create_unit_abbreviations('27.LK')
    '27 LK # 27. LK. # 27.LK # 27.LK. # 27LK # 27 LK # 27. LK. # 27.LK # 27.LK. # 27LK'
    >>> _create_unit_abbreviations('P/L Ilmarinen')
    'P./L Ilmarinen # P./L. Ilmarinen. # P./L.Ilmarinen. # P./LIlmarinen # P/L Ilmarinen # P/L. Ilmarinen. # P/L.Ilmarinen. # P/LIlmarinen # L Ilmarinen # L. Ilmarinen. # L.Ilmarinen. # LIlmarinen # P # P.'
    >>> '27. Pion.K.' in _create_unit_abbreviations('27.Pion.K.')
    True
    """

    # TODO: Copy-pasted from casualties linking, should use this commonly if no customization needed

    def _split(part):
        return [a for a, b in re.findall(r'(\w+?)(\b|(?<=[a-zäö])(?=[A-ZÄÖ]))', part)]
        # return [p.strip() for p in part.split('.')]

    def _variations(part):
        inner_parts = _split(part) + ['']

        spacecombos = list(itertools.product(['.', '. '], repeat=len(inner_parts) - 1))
        combined = [tuple(zip(inner_parts, spacecombo)) for spacecombo in spacecombos]
        combined_strings = [''.join(cc[0] + cc[1] for cc in inner).strip() for inner in combined]

        variations = list(set(combined_strings))
        # variations += ['.'.join(inner_parts)]
        # variations += ['. '.join(inner_parts)]
        variations += [' '.join(inner_parts)]
        variations += [''.join(inner_parts)]
        return sorted(variations)

    variation_lists = [_variations(part) + [part] for part in text.split('/')]

    combined_variations = sorted(set(['/'.join(combined).strip().replace(' /', '/')
                                      for combined in sorted(set(itertools.product(*variation_lists)))]))

    variationset = set(variation.strip() for var_list in variation_lists for variation in var_list
                       if not re.search(r'^[0-9](\.)?$', variation.strip()))

    return ' # '.join(combined_variations) + ' # ' + ' # '.join(sorted(variationset))


class UnitValidator:

    def __init__(self, graph):
        """
        :type graph: Graph
        """
        self.graph = graph

    def validate(self, results, text, prisoner):
        if not results:
            return results

        filtered = []

        for unit in results:
            unit_begin = None
            unit_end = None
            name = None
            try:
                name = unit['properties']['label'][0].split('"')[1]
                unit_begin = unit['properties']['begin'][0].split('"')[1]
                unit_end = unit['properties']['end'][0].split('"')[1]
            except (TypeError, KeyError):
                log.warning('Unable to read data for validation for {uri} , skipping result...'.format(uri=unit))
                continue

            prisoner_caught = str(self.graph.value(prisoner, SCHEMA_NS.time_captured))

            print(text)
            print(name)
            if fuzz.token_set_ratio(text, name) < 80:
                print(fuzz.token_set_ratio(text, name))
                continue

            if unit_begin and unit_begin > prisoner_caught:
                if unit_end and prisoner_caught > unit_end:
                    continue

            filtered.append(unit)

        if len(filtered) == 1:
            return filtered
        elif len(filtered) > 1:
            pprint(len(results))
            pprint(len(filtered))
            return filtered

        pprint(filtered)
        quit()
        return []


def link_units(graph, endpoint):
    """
    Link military units in graph.

    :param graph: Data in RDFLib Graph object
    :param endpoint: Endpoint to query
    :param prop: Property used to give military unit (used for both source and target)
    :return: RDFLib Graph with updated links
    """
    def preprocess(literal, prisoner, subgraph):
        return _create_unit_abbreviations(str(literal).strip())

    def split_by_war(pgraph: Graph):
        for person in pgraph[:RDF.type:SCHEMA_NS.PrisonerOfWar]:
            time_captured = pgraph.value(person, SCHEMA_NS.time_captured)  # Assume duplicates are from same war
            stime = str(time_captured).lower()
            unit = pgraph.value(person, SCHEMA_NS.unit)  # Expecting only one unit per person

            if not unit:
                continue

            pgraph.remove((person, SCHEMA_NS.unit, None))

            if stime <= '1941-06-25' or stime == 'talvisota':
                pgraph.add((person, SCHEMA_NS.unit_winter, unit))
            else:
                pgraph.add((person, SCHEMA_NS.unit_continuation, unit))

        return pgraph

    # query = "PREFIX text: <http://jena.apache.org/text#>" \
    #         "PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>" \
    #         "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" \
    #         "SELECT ?id ?label (min(?conflict_start) as ?begin) (max(?conflict_end) as ?end) {" \
    #         "  ?id a <http://ldf.fi/warsa/actors/actor_types/MilitaryUnit> ." \
    #         "  OPTIONAL {?id <http://ldf.fi/warsa/actors/hasConflict>/crm:P4_has_time-span/crm:P82a_begin_of_the_begin" \
    #         "        ?conflict_start ." \
    #         "    ?id <http://ldf.fi/warsa/actors/hasConflict>/crm:P4_has_time-span/crm:P82b_end_of_the_end" \
    #         "        ?conflict_end . }" \
    #         "  ?id rdfs:label ?label ." \
    #         "  ?id text:query \"<VALUES>\" ." \
    #         "} GROUP BY ?id ?label"
    # # TODO: skos:prefLabel, skos:altLabel
    #
    # arpa = ArpaMimic(query, url=endpoint, retries=3, wait_between_tries=3)

    graph = split_by_war(graph)
    log.debug('Found %s winter war units to link' % len(list(graph[:SCHEMA_NS.unit_winter:])))
    log.debug('Found %s continuation war units to link' % len(list(graph[:SCHEMA_NS.unit_continuation:])))

    arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa_actor_units_winterwar')
    res = arpafy(graph, SCHEMA_NS.unit_linked, arpa, SCHEMA_NS.unit_winter,
                    preprocessor=_create_unit_abbreviations, progress=True)

    print(res)

    arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa_actor_units_continuationwar')
    res = arpafy(graph, SCHEMA_NS.unit_linked, arpa, SCHEMA_NS.unit_continuation,
                    preprocessor=_create_unit_abbreviations, progress=True)

    print(res)

    return graph

    # return link(graph, arpa, SCHEMA_NS.unit, preprocess=preprocess, validator=UnitValidator(graph))


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="War prisoner linking tasks", fromfile_prefix_chars='@')

    argparser.add_argument("task", help="Linking task to perform", choices=["ranks", "units"])
    argparser.add_argument("input", help="Input RDF file")
    argparser.add_argument("output", help="Output file location")
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    argparser.add_argument("--endpoint", default='http://localhost:3030/warsa/sparql', help="SPARQL Endpoint")

    args = argparser.parse_args()

    logging.basicConfig(filename='prisoners.log',
                        filemode='a',
                        level=getattr(logging, args.loglevel),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log = logging.getLogger(__name__)

    input_graph = Graph()
    input_graph.parse(args.input, format=guess_format(args.input))

    if args.task == 'ranks':
        log.info('Linking ranks')
        link_ranks(input_graph, args.endpoint).serialize(args.output, format=guess_format(args.output))

    elif args.task == 'units':
        log.info('Linking units')
        link_units(input_graph, args.endpoint).serialize(args.output, format=guess_format(args.output))


