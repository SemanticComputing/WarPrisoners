#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Hide parts of personal information.
"""
import argparse
import logging

import requests
from datetime import date
from pprint import pprint

from dateutil import parser
from dateutil.relativedelta import relativedelta
from rdflib.util import guess_format

from namespaces import bind_namespaces, SCHEMA_WARSA, SCHEMA_POW, SKOS
from rdflib import Graph, RDF, URIRef, Literal
from rdflib.compare import graph_diff, isomorphic

from csv_to_rdf import get_person_related_triples, get_triple_reifications

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


def remove_triples_and_reifications(graph: Graph, triples: list):
    """
    Remove triples and related reifications from graph
    """
    for triple in triples:
        log.debug('Removing triple and its reifications:  {spo}'.format(spo=str(triple)))
        reifications = get_triple_reifications(graph, triple)

        for reification in reifications:
            graph.remove(reification)

        graph.remove(triple)

    return graph


def hide_health_information(graph: Graph, person: URIRef):
    """
    Hide health information of a person record
    """
    triples = list(graph.triples((person, SCHEMA_POW.cause_of_death, None)))
    triples += list(graph.triples((person, SCHEMA_POW.additional_information, None)))

    graph = remove_triples_and_reifications(graph, triples)

    return graph


def hide_personal_information(graph: Graph, person: URIRef, common_names: list):
    """
    Hide personal information of a person record
    """
    triples = list(graph.triples((person, SCHEMA_WARSA.given_names, None)))
    triples += list(graph.triples((person, SCHEMA_POW.original_name, None)))
    triples += list(graph.triples((person, SKOS.prefLabel, None)))
    triples += list(graph.triples((person, SCHEMA_WARSA.date_of_birth, None)))
    triples += list(graph.triples((person, SCHEMA_POW.date_of_going_mia, None)))
    triples += list(graph.triples((person, SCHEMA_POW.place_of_going_mia_literal, None)))
    triples += list(graph.triples((person, SCHEMA_POW.date_of_capture, None)))
    triples += list(graph.triples((person, SCHEMA_POW.date_of_return, None)))
    triples += list(graph.triples((person, SCHEMA_WARSA.municipality_of_birth_literal, None)))
    triples += list(graph.triples((person, SCHEMA_POW.municipality_of_domicile_literal, None)))
    triples += list(graph.triples((person, SCHEMA_POW.municipality_of_residence_literal, None)))
    triples += list(graph.triples((person, SCHEMA_POW.municipality_of_death_literal, None)))
    triples += list(graph.triples((person, SCHEMA_POW.photograph, None)))
    triples += list(graph.triples((person, SCHEMA_POW.radio_report, None)))
    triples += list(graph.triples((person, SCHEMA_POW.recording, None)))
    triples += list(graph.triples((person, SCHEMA_POW.finnish_return_interrogation_file, None)))

    family_name = str(graph.value(person, SCHEMA_WARSA.family_name))

    if family_name not in common_names:
        log.info('Hiding family name %s of record %s' % (family_name, person))

        triples += list(graph.triples((person, SCHEMA_WARSA.family_name, None)))

        graph.add((person, SCHEMA_WARSA.family_name, Literal("Tuntematon")))
        graph.add((person, SCHEMA_WARSA.given_names, Literal("Sotilas")))
        graph.add((person, SKOS.prefLabel, Literal("Tuntematon, Sotilas")))

    graph = remove_triples_and_reifications(graph, triples)

    graph.add((person, SCHEMA_POW.personal_information_removed, Literal(True)))

    return graph


def fetch_common_names(prisoner_familynames: list, endpoint: str):
    """
    Retrieve common names from endpoint, combine them with persons list and return them as a list
    """
    NAME_QUERY = '''PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?fam ?count WHERE {
        { SELECT ?fam (count(*) as ?count) {
                ?sub foaf:familyName ?fam .
                } GROUP BY ?fam
            }
            FILTER(?count >= 2)
        } ORDER BY ?fam
    '''

    good_names = []
    results = requests.post(endpoint, {'query': NAME_QUERY}).json()

    for result in results['results']['bindings']:
        family_name = result['fam']['value']
        count = int(result['count']['value'])

        if count + prisoner_familynames.count(family_name) >= 4:
            good_names.append(family_name)
            log.debug('Declared %s as a common family name (hits %s + %s)' %
                      (family_name, count, prisoner_familynames.count(family_name)))

    return good_names


def prune_persons(graph: Graph, endpoint: str):
    """
    Hide information of people in graph if needed
    """
    familynames = [str(name) for name in graph.objects(None, SCHEMA_WARSA.family_name)]
    common_names = fetch_common_names(familynames, endpoint)

    persons = list(graph.subjects(RDF.type, SCHEMA_WARSA.PrisonerRecord))

    log.info('Got %s person records for pruning' % len(persons))
    died_recently = []
    possibly_alive = []
    n_public = 0

    # Identify people who might have died less than 50 years age, and who might still be alive

    for person in persons:
        death_dates = list(graph.objects(person, SCHEMA_POW.date_of_death))
        death_dates = [cast_date(d) for d in death_dates]

        death_without_date = any(True for d in death_dates if d is None)
        death_dates = [d for d in death_dates if d is not None]

        if len(death_dates) > 1:
            log.info('Multiple death dates for %s  (using latest)' % person)

        death_date = sorted(death_dates)[-1] if death_dates else None

        if (death_date and (death_date >= date.today() - relativedelta(years=50))) or death_without_date:
            died_recently.append(person)
        else:
            if not (death_date or death_without_date):
                dob = graph.value(person, SCHEMA_WARSA.date_of_birth)
                if dob and cast_date(dob) >= date(1911, 1, 1):
                    possibly_alive.append(person)
            else:
                log.debug('Person record with death date %s declared public')
                n_public += 1

    # Health information is hidden

    for person in died_recently + possibly_alive:
        log.debug('Hiding health information of %s' % person)
        graph = hide_health_information(graph, person)
        graph.add((person, SCHEMA_POW.hide_documents, Literal(True)))

    # Personal information is hidden

    for person in possibly_alive:
        log.debug('Hiding personal information of %s' % person)
        graph = hide_personal_information(graph, person, common_names)

    log.info('Persons that have died more than 50 years ago: %s' % n_public)
    log.info('Persons suspected to have died less than 50 years ago: %s' % len(died_recently))
    log.info('Persons that might be alive: %s' % len(possibly_alive))

    return graph


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description=__doc__, fromfile_prefix_chars='@')
    argparser.add_argument("input", help="Input RDFfile")
    argparser.add_argument("output", help="Output RDF file")
    argparser.add_argument("--endpoint", default='http://localhost:3030/warsa/sparql', help="SPARQL Endpoint")
    argparser.add_argument("--logfile", default='tasks.log', help="Logfile")
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    args = argparser.parse_args()

    log = logging.getLogger()  # Get root logger
    log_handler = logging.FileHandler(args.logfile)
    log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    log.addHandler(log_handler)
    log.setLevel(args.loglevel)

    g = Graph()

    g.parse(args.input, format='turtle')

    bind_namespaces(prune_persons(g, args.endpoint)).serialize(args.output, format=guess_format(args.output))
