"""
Stand-alone tasks for war prisoners dataset
"""

import argparse
import logging
from io import StringIO
from time import sleep

from rdflib import *
from SPARQLWrapper import SPARQLWrapper, JSON

ns_skos = Namespace('http://www.w3.org/2004/02/skos/core#')
ns_dct = Namespace('http://purl.org/dc/terms/')
ns_schema = Namespace('http://ldf.fi/schema/narc-menehtyneet1939-45/')
ns_crm = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
ns_foaf = Namespace('http://xmlns.com/foaf/0.1/')
ns_owl = Namespace('http://www.w3.org/2002/07/owl#')

ns_hautausmaat = Namespace('http://ldf.fi/narc-menehtyneet1939-45/hautausmaat/')
ns_kansalaisuus = Namespace('http://ldf.fi/narc-menehtyneet1939-45/kansalaisuus/')
ns_kansallisuus = Namespace('http://ldf.fi/narc-menehtyneet1939-45/kansallisuus/')
ns_kunnat = Namespace('http://ldf.fi/narc-menehtyneet1939-45/kunnat/')
ns_sotilasarvo = Namespace('http://ldf.fi/narc-menehtyneet1939-45/sotilasarvo/')
ns_menehtymisluokka = Namespace('http://ldf.fi/narc-menehtyneet1939-45/menehtymisluokka/')


argparser = argparse.ArgumentParser(description="Stand-alone tasks for war prisoners dataset", fromfile_prefix_chars='@')

argparser.add_argument("task", help="Which task to run", choices=["documents_links", "test"])
argparser.add_argument("input", help="Input RDF data file")
argparser.add_argument("output", help="Output RDF data file")

argparser.add_argument("--endpoint", default='http://ldf.fi/warsa/sparql', type=str, help="SPARQL endpoint")
argparser.add_argument("--format", default='turtle', type=str, help="Format of RDF files [default: turtle]")
argparser.add_argument("--loglevel", default='INFO',
                       choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Logging level, default is INFO.")

args = argparser.parse_args()

logging.basicConfig(filename='tasks.log', filemode='a', level=getattr(logging, args.loglevel.upper()),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log = logging.getLogger(__name__)
log.info('Starting to run tasks with arguments: {args}'.format(args=args))


def _query_sparql(sparql_obj):
    """
    Query SPARQL with retry functionality

    :type sparql_obj: SPARQLWrapper
    :return: SPARQL query results
    """
    results = None
    retry = 0
    while not results:
        try:
            results = sparql_obj.query().convert()
        except ValueError:
            if retry < 50:
                log.error('Malformed result for query {p_uri}, retrying in 10 seconds...'.format(
                    p_uri=sparql_obj.queryString))
                retry += 1
                sleep(10)
            else:
                raise
    log.debug('Got results {res} for query {q}'.format(res=results, q=sparql_obj.queryString))
    return results


def load_input_file(filename):
    """
    >>> load_input_file(StringIO('<http://example.com/res> a <http://example.com/class> .'))  #doctest: +ELLIPSIS
    <Graph identifier=...(<class 'rdflib.graph.Graph'>)>
    """
    return Graph().parse(filename, format=args.format)

if args.task == '':
    log.info('Loading input file...')
    death_records = load_input_file(args.input)
    log.info('Creating links...')
    documents_links(death_records, args.endpoint)
    log.info('Serializing output file...')
    death_records.serialize(format=args.format, destination=args.output)

elif args.task == 'test':
    print('Running doctests')
    import doctest

    res = doctest.testmod()
    if not res[0]:
        print('Doctests OK!')
    exit()

log.info('All done.')
