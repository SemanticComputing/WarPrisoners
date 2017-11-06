#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Remove persons that have died less than 50 years ago.
"""
import argparse
import logging
from datetime import date

from dateutil import parser
from dateutil.relativedelta import relativedelta
from rdflib import Graph, RDF, Namespace

from namespaces import bind_namespaces, WARSA_NS, DATA_NS, SCHEMA_NS

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


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument("input", help="Input file")
    args = argparser.parse_args()

    g = Graph()
    pruned = Graph()
    nonpruned = Graph()

    g.parse(args.input, format='turtle')

    persons = list(g.subjects(RDF.type, WARSA_NS.PrisonerRecord))
    print('Found %s persons' % len(list(persons)))

    for person in persons:
        person_death = [cast_date(d) for d in g.objects(person, SCHEMA_NS.death_date)]

        if not len(person_death):
            person_death = [cast_date(d) for d in g.objects(person, SCHEMA_NS.declared_death)]

        person_death = [d for d in person_death if d is not None]

        if not person_death:
            if (not g.value(subject=person, predicate=SCHEMA_NS.returned_date) and
                    g.value(subject=person, predicate=SCHEMA_NS.death_date)):
                person_death = [date(1900, 1, 1)]  # Do not prune if completely unknown
            else:
                person_death = [date.today()]

        person_death = sorted(person_death)[-1]

        if person_death <= date.today() - relativedelta(years=50):
            for (s, p, o) in g.triples((person, None, None)):
                nonpruned.add((s, p, o))
        else:
            for (s, p, o) in g.triples((person, None, None)):
                pruned.add((s, p, o))

    print('Nonpruned persons: %s' % len(list(nonpruned.subjects(RDF.type, WARSA_NS.PrisonerRecord))))
    print('Pruned persons: %s' % len(list(pruned.subjects(RDF.type, WARSA_NS.PrisonerRecord))))

    bind_namespaces(pruned)
    bind_namespaces(nonpruned)

    pruned.serialize(format="turtle", destination=args.input + '.secret.ttl')
    nonpruned.serialize(format="turtle", destination=args.input + '.public.ttl')
