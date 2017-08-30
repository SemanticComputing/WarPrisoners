#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""

import argparse
import logging
import re
from pprint import pprint

from SPARQLWrapper import SPARQLWrapper
from fuzzywuzzy import fuzz
from rdflib import Graph, Literal
from rdflib import URIRef
from rdflib.util import guess_format

from arpa_linker.arpa import ArpaMimic, Arpa, combine_values, process_graph
from namespaces import *
from warsa_linkers.units import preprocessor, Validator


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

    # TODO: Return only links, not the whole graph

    def preprocess(literal, prisoner, subgraph):
        value = re.sub(r'[/\-]', ' ', str(literal)).strip()
        return mapping[value] if value in mapping else value

    mapping = {'kaart': 'stm',
               'aliluutn': 'aliluutnantti'}

    query = "PREFIX text: <http://jena.apache.org/text#> " + \
            "SELECT * { ?id a <http://ldf.fi/warsa/actors/ranks/Rank> . " + \
            "?id text:query \"<VALUES>\" . " + \
            "}"

    arpa = ArpaMimic(query, url=endpoint, retries=3, wait_between_tries=3)

    return link(graph, arpa, SCHEMA_NS.rank, preprocess=preprocess)


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
    :return: RDFLib Graph with ONLY unit links
    """
    def get_query_template():
        with open('SPARQL/units.sparql') as f:
            return f.read()

    temp_graph = Graph()

    ngram_arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa_casualties_actor_units', retries=10, wait_between_tries=6)

    for person in graph[:RDF.type:SCHEMA_NS.PrisonerOfWar]:

        captured_date = str(graph.value(person, SCHEMA_NS.time_captured))
        if captured_date < '1941-06-25':
            temp_graph.add((person, URIRef('http://ldf.fi/schema/warsa/events/related_period'),
                            URIRef('http://ldf.fi/warsa/conflicts/WinterWar')))

        unit = preprocessor(str(graph.value(person, SCHEMA_NS.unit)))
        ngrams = ngram_arpa.get_candidates(unit)
        combined = combine_values(ngrams['results'])
        temp_graph.add((person, SCHEMA_NS.candidate, Literal(combined)))

    log.info('Linking the found candidates')
    arpa = ArpaMimic(get_query_template(), endpoint, retries=10, wait_between_tries=6)
    new_graph = process_graph(temp_graph, SCHEMA_NS.osasto, arpa, progress=True,
                              validator=Validator(temp_graph), new_graph=True, source_prop=SCHEMA_NS.candidate)
    return new_graph['graph']


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
