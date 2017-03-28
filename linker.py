#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""

import argparse
import logging
import re

import itertools

from arpa_linker.arpa import ArpaMimic
from rdflib import Graph
from rdflib import URIRef
from rdflib.util import guess_format

from namespaces import *


def link(graph, endpoint, prop, query, preprocess=lambda x: x, mapping=None, validate=None):
    """
    Link entities based on parameters
    
    :return: 
    """
    if not mapping:
        mapping = {}

    prop_str = str(prop).split('/')[-1]  # Used for logging

    arpa = ArpaMimic(query, url=endpoint, retries=3, wait_between_tries=3)

    for (prisoner, value_literal) in list(graph[:prop:]):
        value = str(value_literal).strip()
        value = preprocess(value)
        value = mapping[value] if value in mapping else value

        if value != str(value_literal):
            logger.info('Changed %s %s into %s for linking' % (prop_str, value_literal, value))

        if value:
            res = arpa.query(value)
            if res:
                res = res[0]['id']
                logger.debug('Found a matching {ps} for {val}: {res}'.format(ps=prop_str, val=value, res=res))

                if validate and not validate(res):
                    logger.info('Match {res} failed validation for {val}, skipping it')
                    continue

                # Update property to found value
                graph.remove((prisoner, prop, value_literal))
                graph.add((prisoner, prop, URIRef(res)))

                # TODO: Update reifications
            else:
                logger.warning('No match found for %s: %s' % (prop_str, value))

    return graph


def link_ranks(graph, endpoint):
    """
    Link military ranks in graph.

    :param graph: Data in RDFLib Graph object 
    :param endpoint: Endpoint to query military ranks from
    :param prop: Property used to give military rank (used for both source and target) 
    :return: RDFLib Graph with updated links
    """
    preprocess = lambda literal: re.sub(r'[/\-]', ' ', str(literal)).strip()

    mapping = {'kaart': 'stm',
               'aliluutn': 'aliluutnantti'}

    query = "PREFIX text: <http://jena.apache.org/text#> " +\
            "SELECT * { ?id a <http://ldf.fi/warsa/actors/ranks/Rank> . " +\
            "?id text:query \"<VALUES>\" . " +\
            "}"

    return link(graph, endpoint, SCHEMA_NS.rank, query, preprocess=preprocess, mapping=mapping)


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
    """

    # TODO: Copy-pasted from casualties linking, should use this commonly if no customization needed

    def _split(part):
        return [a for a, b in re.findall(r'(\w+?)(\b|(?<=[a-zäö])(?=[A-ZÄÖ]))', part)]
        # return [p.strip() for p in part.split('.')]

    def _variations(part):
        inner_parts = _split(part) + ['']
        variations = []
        variations += ['.'.join(inner_parts)]
        variations += ['. '.join(inner_parts)]
        variations += [' '.join(inner_parts)]
        variations += [''.join(inner_parts)]
        return variations

    variation_lists = [_variations(part) + [part] for part in text.split('/')]

    combined_variations = sorted(set(['/'.join(combined).strip().replace(' /', '/')
                                      for combined in sorted(set(itertools.product(*variation_lists)))]))

    variationset = set(variation.strip() for var_list in variation_lists for variation in var_list
                       if not re.search(r'^[0-9](\.)?$', variation.strip()))

    return ' # '.join(combined_variations) + ' # ' + ' # '.join(sorted(variationset))


def link_units(graph, endpoint):
    """
    Link military units in graph.

    :param graph: Data in RDFLib Graph object
    :param endpoint: Endpoint to query
    :param prop: Property used to give military unit (used for both source and target)
    :return: RDFLib Graph with updated links
    """
    preprocess = lambda literal: _create_unit_abbreviations(str(literal).strip())

    mapping = {}

    query = "PREFIX text: <http://jena.apache.org/text#> " \
            "PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/> " \
            "SELECT * { ?id a <http://ldf.fi/warsa/actors/actor_types/MilitaryUnit> . " \
            "?id <http://ldf.fi/warsa/actors/hasConflict>/crm:P82a_begin_of_the_begin " \
            "    ?conflict_start . " \
            "?id <http://ldf.fi/warsa/actors/hasConflict>/crm:P82b_end_of_the_end " \
            "    ?conflict_end . " \
            "?id text:query \"<VALUES>\" . " \
            "}"

    return link(graph, endpoint, SCHEMA_NS.unit, query, preprocess=preprocess, mapping=mapping, validate=print)


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

    logger = logging.getLogger(__name__)

    input_graph = Graph()
    input_graph.parse(args.input, format=guess_format(args.input))

    if args.task == 'ranks':
        logger.info('Linking ranks')
        link_ranks(input_graph, args.endpoint).serialize(args.output, format=guess_format(args.output))

    elif args.task == 'units':
        logger.info('Linking units')
        link_units(input_graph, args.endpoint).serialize(args.output, format=guess_format(args.output))


