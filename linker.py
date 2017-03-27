#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""
import argparse
import logging

from arpa_linker.arpa import ArpaMimic, arpafy
from rdflib import Graph
from rdflib.util import guess_format

from namespaces import *


def link_ranks(graph, endpoint, rdf_class=SCHEMA_NS.PrisonerOfWar):
    """
    Link military ranks in graph

    :param graph:
    :param endpoint:
    :param rdf_class:
    :return:
    """
    MAPPING = {'-': ''}

    query = "PREFIX text: <http://jena.apache.org/text#> " +\
            "SELECT * { ?id a <http://ldf.fi/warsa/actors/ranks/Rank> . " +\
            "?id text:query \"<VALUES>\" . " +\
            "}"

    arpa = ArpaMimic(query.replace("\n", ""), url=endpoint, retries=3, wait_between_tries=3)

    for prisoner in graph[:RDF.type:rdf_class]:
        rank = graph.value(subject=prisoner, predicate=SCHEMA_NS.rank)
        if rank:
            res = arpa.query(MAPPING[rank] if rank in MAPPING else rank.replace('/', '\\\\/'))
            if res:
                res = res[0]['id']
                logger.debug('{rank} --> {res}'.format(rank=rank, res=res))
            else:
                logger.warning('No match found for rank %s' % rank)
        else:
            logger.info('Empty rank for p')


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="War prisoner linking tasks", fromfile_prefix_chars='@')

    argparser.add_argument("task", help="Linking task to perform", choices=["ranks", "units"])
    argparser.add_argument("input", help="Input RDF file")
    argparser.add_argument("output", help="Output file location")
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    argparser.add_argument("--endpoint", default='http://localhost:3030/warsa/sparql', help="SPARQL Endpoint")

    args = argparser.parse_args()

    logging.basicConfig(filename='linker.log',
                        filemode='a',
                        level=getattr(logging, args.loglevel),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)

    input_graph = Graph()
    logger.info('Parsing file {}'.format(args.input))
    input_graph.parse(args.input, format=guess_format(args.input))

    if args.task == 'ranks':
        logger.info('Linking ranks')
        link_ranks(input_graph, args.endpoint)

