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
from namespaces import SCHEMA_NS, RDF, SKOS, FOAF


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
    new_graph = Graph()

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

                # TODO: Update reifications
            else:
                log.warning('No match found for %s: %s' % (prop_str, value))

    return target_graph


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
        return rank_mapping[value] if value in rank_mapping else value

    rank_mapping = {
        'kaart': 'stm',
        'aliluutn': 'aliluutnantti',
        'lääk.alik': 'lääkintäalikersantti',
        'lääk.stm': 'lääkintäsotamies',
        'ups.kok': 'upseerikokelas',
    }

    query = "PREFIX text: <http://jena.apache.org/text#> " + \
            "SELECT * { ?id a <http://ldf.fi/schema/warsa/Rank> . " + \
            "?id text:query \"<VALUES>\" . " + \
            "}"

    arpa = ArpaMimic(query, url=endpoint, retries=3, wait_between_tries=3)

    return link(graph, arpa, SCHEMA_NS.rank, Graph(), SCHEMA_NS.warsa_rank, preprocess=preprocess)


class PersonValidator:
    def __init__(self, graph, birthdate_prop, deathdate_prop, source_rank_prop,
                 source_firstname_prop, source_lastname_prop):
        self.graph = graph
        self.birthdate_prop = birthdate_prop
        self.deathdate_prop = deathdate_prop
        self.source_rank_prop = source_rank_prop
        self.source_firstname_prop = source_firstname_prop
        self.source_lastname_prop = source_lastname_prop

    def validate(self, results, text, s):
        if not results:
            return results

        rank = self.graph.value(s, self.source_rank_prop)
        firstnames = str(self.graph.value(s, self.source_firstname_prop)).replace('/', ' ').lower().split()
        lastname = str(self.graph.value(s, self.source_lastname_prop)).replace('/', ' ').lower()

        filtered = []
        _FUZZY_LASTNAME_MATCH_LIMIT = 50
        _FUZZY_FIRSTNAME_MATCH_LIMIT = 60

        for person in results:
            score = 0
            res_id = None
            try:
                res_id = person['properties'].get('id')[0].replace('"', '')
                res_ranks = [r.replace('"', '').lower() for r in person['properties'].get('rank_id', [''])]

                res_lastname = person['properties'].get('sukunimi')[0].replace('"', '').lower()
                res_firstnames = person['properties'].get('etunimet')[0].split('^')[0].replace('"', '').lower()
                res_firstnames = res_firstnames.split()

                res_birthdates = (min(person['properties'].get('birth_start', [''])).split('^')[0].replace('"', ''),
                                  max(person['properties'].get('birth_end', [''])).split('^')[0].replace('"', ''))
                res_deathdates = (min(person['properties'].get('death_start', [''])).split('^')[0].replace('"', ''),
                                  max(person['properties'].get('death_end', [''])).split('^')[0].replace('"', ''))

            except TypeError:
                log.info('Unable to read data for validation for {uri} , skipping result...'.format(uri=res_id))
                continue

            log.debug('Potential match for person {p1text} <{p1}> : {p2text} {p2}'.
                      format(p1text=' '.join([rank] + firstnames + [lastname]),
                             p1=s,
                             p2text=' '.join(res_ranks + res_firstnames + [res_lastname]),
                             p2=res_id))

            fuzzy_lastname_match = fuzz.token_set_ratio(lastname, res_lastname, force_ascii=False)

            if fuzzy_lastname_match >= _FUZZY_LASTNAME_MATCH_LIMIT:
                log.debug('Fuzzy last name match for {f1} and {f2}: {fuzzy}'
                          .format(f1=lastname, f2=res_lastname, fuzzy=fuzzy_lastname_match))
                score += int((fuzzy_lastname_match - _FUZZY_LASTNAME_MATCH_LIMIT) /
                             (100 - _FUZZY_LASTNAME_MATCH_LIMIT) * 100)

            if rank and res_ranks and rank != 'tuntematon':
                if rank in res_ranks:
                    score += 25
                    if rank not in [URIRef('http://ldf.fi/warsa/actors/ranks/Sotamies'), URIRef('http://ldf.fi/warsa/actors/ranks/Korpraali')]:
                        # More than half of the casualties have rank private and about 15% are corporals.
                        # Give points to ranks higher than these.
                        score += 25
                else:
                    score -= 25

            birthdate = str(self.graph.value(s, self.birthdate_prop))
            deathdate = str(self.graph.value(s, self.deathdate_prop))

            if res_birthdates[0] and birthdate:
                if res_birthdates[0] <= birthdate:
                    if res_birthdates[0] == birthdate:
                        score += 50
                else:
                    score -= 25

            if res_birthdates[1] and birthdate:
                if birthdate <= res_birthdates[1]:
                    if res_birthdates[1] == birthdate:
                        score += 50
                else:
                    score -= 25

            # If both are single dates, allow one different character before penalizing
            if res_birthdates[0] and res_birthdates[0] == res_birthdates[1] and \
               fuzz.partial_ratio(res_birthdates[0], birthdate) <= 80:
                score -= 25

            if res_deathdates[0] and deathdate:
                if res_deathdates[0] <= deathdate:
                    if res_deathdates[0] == deathdate:
                        score += 50
                else:
                    score -= 25

            if res_deathdates[1] and deathdate:
                if deathdate <= res_deathdates[1]:
                    if deathdate == res_deathdates[1]:
                        score += 50
                else:
                    score -= 25

            # If both are single dates, allow one different character before penalizing
            if res_deathdates[0] and res_deathdates[0] == res_deathdates[1] and \
               fuzz.partial_ratio(res_deathdates[0], deathdate) <= 80:
                score -= 25

            s_first1 = ' '.join(firstnames)
            s_first2 = ' '.join(res_firstnames)
            fuzzy_firstname_match = max(fuzz.partial_ratio(s_first1, s_first2),
                                        fuzz.token_sort_ratio(s_first1, s_first2, force_ascii=False),
                                        fuzz.token_set_ratio(s_first1, s_first2, force_ascii=False))

            if fuzzy_firstname_match >= _FUZZY_FIRSTNAME_MATCH_LIMIT:
                log.debug('Fuzzy first name match for {f1} and {f2}: {fuzzy}'
                          .format(f1=firstnames, f2=res_firstnames, fuzzy=fuzzy_firstname_match))
                score += int((fuzzy_firstname_match - _FUZZY_FIRSTNAME_MATCH_LIMIT) /
                             (100 - _FUZZY_FIRSTNAME_MATCH_LIMIT) * 100)
            else:
                log.debug('No fuzzy first name match for {f1} and {f2}: {fuzzy}'
                          .format(f1=firstnames, f2=res_firstnames, fuzzy=fuzzy_firstname_match))

            person['score'] = score

            if score > 210:
                filtered.append(person)

                log.info('Found matching Warsa person for {rank} {fn} {ln} {uri} : '
                         '{res_rank} {res_fn} {res_ln} {res_uri} [score: {score}]'
                         .format(rank=rank, fn=s_first1, ln=lastname, uri=s, res_rank=res_ranks, res_fn=s_first2,
                                 res_ln=res_lastname, res_uri=res_id, score=score))
            else:
                log.info('Skipping potential match because of too low score [{score}]: {p1}  <<-->>  {p2}'.
                         format(p1=s, p2=res_id, score=score))

        if len(filtered) == 1:
            return filtered
        elif len(filtered) > 1:
            log.warning('Found several matches for Warsa person {s} ({text}): {ids}'.
                        format(s=s, text=text,
                               ids=', '.join(p['properties'].get('id')[0].split('^')[0].replace('"', '')
                                             for p in filtered)))

            best_matches = sorted(filtered, key=lambda p: p['score'], reverse=True)
            log.warning('Choosing best match: {id}'.format(id=best_matches[0].get('id')))
            return [best_matches[0]]

        return []


def link_persons(graph, endpoint):
    """
    Link military persons in graph.

    :param graph: Data in RDFLib Graph object
    :param endpoint: Endpoint to query persons from
    :return: RDFLib Graph with updated links
    """

    def get_query_template():
        with open('sparql/persons.sparql') as f:
            return f.read()

    validator = PersonValidator(graph, SCHEMA_NS.birth_date, SCHEMA_NS.death_date,
            SCHEMA_NS.warsa_rank, FOAF.givenName, FOAF.familyName)
    arpa = ArpaMimic(get_query_template(), endpoint, retries=10, wait_between_tries=6)
    new_graph = process_graph(graph, SCHEMA_NS.person, arpa, progress=True,
                              validator=validator, new_graph=True, source_prop=SKOS.prefLabel)
    return new_graph['graph']


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


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="War prisoner linking tasks", fromfile_prefix_chars='@')

    argparser.add_argument("task", help="Linking task to perform", choices=["ranks", "persons"])
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

    elif args.task == 'persons':
        log.info('Linking persons')
        link_persons(input_graph, args.endpoint).serialize(args.output, format=guess_format(args.output))
