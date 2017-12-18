#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Remove persons that have died less than 50 years ago.
"""
import argparse
import logging
from datetime import date
from pprint import pprint

from dateutil import parser
from dateutil.relativedelta import relativedelta
from rdflib import Graph, RDF, Namespace
from rdflib.compare import graph_diff, isomorphic

from csv_to_rdf import get_triple_reifications, get_person_related_triples
from namespaces import bind_namespaces, WARSA_NS, DATA_NS, SCHEMA_NS

logging.basicConfig(filename='prisoners.log', filemode='a', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log = logging.getLogger(__name__)


def cast_date(orig_date: str):
    datestr = orig_date.strip('Xx-')
    cast = None

    try:
        cast = parser.parse(datestr).date()
    except ValueError:
        try:
            cast = parser.parse(datestr[-4:]).date()
        except ValueError:
            log.warning('Bad date: %s' % orig_date)

    return cast


def prune_persons(graph):
    pruned = Graph()
    nonpruned = Graph()

    persons = list(graph.subjects(RDF.type, WARSA_NS.PrisonerRecord))
    print('Found %s persons' % len(list(persons)))

    for person in persons:
        person_death = [cast_date(d) for d in graph.objects(person, SCHEMA_NS.death_date)]

        if not len(person_death):
            person_death = [cast_date(d) for d in graph.objects(person, SCHEMA_NS.declared_death)]

        person_death = [d for d in person_death if d is not None]

        if not person_death:
            if (not graph.value(subject=person, predicate=SCHEMA_NS.returned_date) and
                    graph.value(subject=person, predicate=SCHEMA_NS.death_date)):
                person_death = [date(1900, 1, 1)]  # Do not prune if completely unknown
            else:
                person_death = [date.today()]

        person_death = sorted(person_death)[-1]

        if person_death <= date.today() - relativedelta(years=50):
            nonpruned += get_person_related_triples(graph, person)
        else:
            pruned += get_person_related_triples(graph, person)

    return pruned, nonpruned


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument("input", help="Input file")
    args = argparser.parse_args()

    g = Graph()

    g.parse(args.input, format='turtle')

    pruned, nonpruned = prune_persons(g)

    print('Nonpruned persons: %s' % len(list(nonpruned.subjects(RDF.type, WARSA_NS.PrisonerRecord))))
    print('Pruned persons: %s' % len(list(pruned.subjects(RDF.type, WARSA_NS.PrisonerRecord))))

    g2 = pruned + nonpruned

    diffs = graph_diff(g, g2)

    print('In new:')
    pprint([d for d in diffs[1]])

    print('In old:')
    pprint([d for d in diffs[2]])

    assert isomorphic(g, g2)

    bind_namespaces(pruned)
    bind_namespaces(nonpruned)

    pruned.serialize(format="turtle", destination=args.input + '.secret.ttl')
    nonpruned.serialize(format="turtle", destination=args.input + '.public.ttl')

