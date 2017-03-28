#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""

import argparse
import logging
import re

from arpa_linker.arpa import ArpaMimic
from rdflib import Graph
from rdflib import URIRef
from rdflib.util import guess_format

from namespaces import *


def link_ranks(graph, endpoint, prop=SCHEMA_NS.rank):
    """
    Link military ranks in graph.

    :param graph: Data in RDFLib Graph object 
    :param endpoint: Endpoint to query military ranks from
    :param prop: Property used to give military rank (used for both source and target) 
    :return: RDFLib Graph with updated links
    """
    MAPPING = {'kaart': 'stm',
               'aliluutn': 'aliluutnantti'}

    query = "PREFIX text: <http://jena.apache.org/text#> " +\
            "SELECT * { ?id a <http://ldf.fi/warsa/actors/ranks/Rank> . " +\
            "?id text:query \"<VALUES>\" . " +\
            "}"

    arpa = ArpaMimic(query.replace("\n", ""), url=endpoint, retries=3, wait_between_tries=3)

    for (prisoner, rank_literal) in list(graph[:prop:]):
        rank = re.sub(r'[/\-]', ' ', str(rank_literal)).strip()
        if rank != str(rank_literal):
            logger.info('Changed rank %s into %s for linking.' % (rank_literal, rank))
        if rank:
            res = arpa.query(MAPPING[rank] if rank in MAPPING else rank)
            if res:
                res = res[0]['id']
                logger.debug('Found a matching rank for {rank}: {res}'.format(rank=rank, res=res))

                # Update property to found value
                graph.remove((prisoner, prop, rank_literal))
                graph.add((prisoner, prop, URIRef(res)))

                # TODO: Update reifications
            else:
                logger.warning('No match found for rank %s' % rank)

    return graph


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

