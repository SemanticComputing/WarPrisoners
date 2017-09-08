#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""War prisoner linking tasks"""

import argparse
import logging
import re
import time
from datetime import datetime

from jellyfish import jaro_winkler
from fuzzywuzzy import fuzz
from rdflib import Graph
from rdflib import URIRef
from rdflib.util import guess_format

from arpa_linker.arpa import ArpaMimic, process_graph
from namespaces import SCHEMA_NS, SKOS, FOAF, CIDOC, BIOC


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
                 source_firstname_prop, source_lastname_prop, disappearance_place_prop,
                 disappearance_date_prop, birth_place_prop, unit_prop, occupation_prop):
        self.graph = graph
        self.birthdate_prop = birthdate_prop
        self.deathdate_prop = deathdate_prop
        self.source_rank_prop = source_rank_prop
        self.source_firstname_prop = source_firstname_prop
        self.source_lastname_prop = source_lastname_prop
        self.birth_place_prop = birth_place_prop
        self.disappearance_place_prop = disappearance_place_prop
        self.unit_prop = unit_prop
        self.occupation_prop = occupation_prop
        self.disappearance_date_prop = disappearance_date_prop

    def validate(self, results, text, s):
        if not results:
            return results

        rank = self.graph.value(s, self.source_rank_prop)
        unit = self.graph.value(s, self.unit_prop)
        firstnames = str(self.graph.value(s, self.source_firstname_prop)).replace('/', ' ').lower().split()
        lastname = str(self.graph.value(s, self.source_lastname_prop)).replace('/', ' ').lower()
        birth_place = (self.graph.value(s, self.birth_place_prop) or '').lower()
        disappearance_place = (self.graph.value(s, self.disappearance_place_prop) or '').lower()
        disappearance_date = (self.graph.value(s, self.disappearance_date_prop) or '').lower()
        occupation = (self.graph.value(s, self.occupation_prop) or '').lower()

        bd = [str(b) for b in self.graph.objects(s, self.birthdate_prop)]
        birthdates = set()
        for b in bd:
            if len(re.findall('x', b, re.I)) < 2:
                birthdates.add(b)

        dd = [str(d) for d in self.graph.objects(s, self.deathdate_prop)]
        deathdates = set()
        for d in dd:
            if len(re.findall('x', d, re.I)) < 2:
                deathdates.add(d)

        disappearance_date = str(self.graph.value(s, self.disappearance_date_prop))
        if len(re.findall('x', disappearance_date, re.I)) > 1:
            disappearance_date = None

        filtered = []
        _FUZZY_LASTNAME_MATCH_LIMIT = 0.5
        _FUZZY_FIRSTNAME_MATCH_LIMIT = 0.5
        DATE_FORMAT = '%Y-%m-%d'

        for person in results:
            score = 0
            res_id = None
            try:
                res_id = person['properties'].get('id')[0].replace('"', '')
                res_ranks = [URIRef(re.sub(r'[<>]', '', r)) for r in person['properties'].get('rank_id', ['']) if r]

                res_lastname = person['properties'].get('sukunimi')[0].replace('"', '').lower()
                res_firstnames = person['properties'].get('etunimet')[0].split('^')[0].replace('"', '').lower()
                res_firstnames = res_firstnames.split()

                res_birth_place = person['properties'].get('birth_place', [''])[0].replace('"', '').lower()
                res_disappearance_place = person['properties'].get('disappearance_place', [''])[0].replace('"', '').lower()
                res_disappearance_date = person['properties'].get('disappearance_date', [''])[0].replace('"', '').lower()
                res_occupation = person['properties'].get('occupation', [''])[0].replace('"', '').lower()
                res_unit = person['properties'].get('unit', [''])[0]
                res_unit = URIRef(re.sub(r'[<>]', '', res_unit)) if res_unit else res_unit

                res_bd = (min(person['properties'].get('birth_start', [''])).split('^')[0].replace('"', ''),
                            max(person['properties'].get('birth_end', [''])).split('^')[0].replace('"', ''))
                res_birthdates = set(filter(bool, res_bd))
                res_dd = (min(person['properties'].get('death_start', [''])).split('^')[0].replace('"', ''),
                            max(person['properties'].get('death_end', [''])).split('^')[0].replace('"', ''))
                res_deathdates = set(filter(bool, res_dd))

            except TypeError:
                log.info('Unable to read data for validation for {uri} , skipping result...'.format(uri=res_id))
                continue

            log.debug('Potential match for person {p1text} <{p1}> : {p2text} {p2}'.
                      format(p1text=' '.join([rank or ''] + firstnames + [lastname]),
                             p1=s,
                             p2text=' '.join(res_ranks + res_firstnames + [res_lastname]),
                             p2=res_id))

            fuzzy_lastname_match = jaro_winkler(lastname, res_lastname)

            if fuzzy_lastname_match >= _FUZZY_LASTNAME_MATCH_LIMIT:
                log.debug('Fuzzy last name match for {f1} and {f2}: {fuzzy}'
                          .format(f1=lastname, f2=res_lastname, fuzzy=fuzzy_lastname_match))
                score += (fuzzy_lastname_match - _FUZZY_LASTNAME_MATCH_LIMIT) / (1 - _FUZZY_LASTNAME_MATCH_LIMIT) * 100

            log.info('Lastname: {b} <-> {rb}: -> {s}'.format(b=lastname, rb=res_lastname, s=score))

            if rank and res_ranks and rank != 'tuntematon':
                if rank in res_ranks:
                    score += 25
                    if rank not in [URIRef('http://ldf.fi/warsa/actors/ranks/Sotamies'), URIRef('http://ldf.fi/warsa/actors/ranks/Korpraali')]:
                        # More than half of the casualties have rank private and about 15% are corporals.
                        # Give points to ranks higher than these.
                        score += 25
                else:
                    score -= 25

            log.info('Rank: {b} <-> {rb}: -> {s}'.format(b=rank, rb=res_ranks, s=score))

            if res_birthdates and birthdates:
                if res_birthdates.issubset(birthdates):
                    score += 100
                elif [d for d in birthdates if res_bd[0] <= d <= res_bd[1]]:
                    score += 50
                else:
                    score -= 25

                # If both are single dates, allow one different character before penalizing more
                if len(res_birthdates) == 1 and max([fuzz.partial_ratio(next(iter(res_birthdates)), d) for d in birthdates] or [0]) <= 80:
                    score -= 25

            log.info('Birth: {b} <-> {rb}: -> {s}'.format(b=birthdates, rb=res_birthdates, s=score))

            try:
                [datetime.strptime(d, DATE_FORMAT) for d in deathdates]
                has_parseable_death_date = True if deathdates else False
            except ValueError:
                has_parseable_death_date = False
                log.warning('Could not parse death date: {date}'.format(date=deathdates))

            ddates = set(deathdates)
            if disappearance_date:
                ddates.add(disappearance_date)
            if res_deathdates and deathdates or res_disappearance_date and disappearance_date:
                if deathdates == res_deathdates or disappearance_date == res_disappearance_date:
                    score += 100
                elif res_deathdates.issubset(ddates) or res_disappearance_date in ddates:
                    score += 50
                elif [d for d in ddates if res_dd[0] <= d <= res_dd[1]]:
                    score += 50
                elif deathdates and not (deathdates & res_deathdates):
                    if has_parseable_death_date:
                        score -= 25
                elif disappearance_date and res_disappearance_date and disappearance_date != res_disappearance_date:
                    if has_parseable_death_date:
                        datetime.strptime(disappearance_date, DATE_FORMAT)
                        score -= 25

            # If both are single dates, allow one different character before penalizing more
            if has_parseable_death_date and len(res_deathdates) == 1 and \
                    max([fuzz.partial_ratio(next(iter(res_deathdates)), d) for d in deathdates]) <= 80:
                score -= 25

            log.info('Death: {b} <-> {rb}: -> {s}'.format(b=ddates, rb=res_deathdates, s=score))

            s_first1 = ' '.join(firstnames)
            s_first2 = ' '.join(res_firstnames)
            fuzzy_firstname_match = fuzz.token_set_ratio(s_first1, s_first2) / 100

            if fuzzy_firstname_match >= _FUZZY_FIRSTNAME_MATCH_LIMIT:
                score += (fuzzy_firstname_match - _FUZZY_FIRSTNAME_MATCH_LIMIT) / (1 - _FUZZY_FIRSTNAME_MATCH_LIMIT) * 75
                log.info('Fuzzy first name match for {f1} and {f2}: {fuzzy} -> {score}'
                          .format(f1=firstnames, f2=res_firstnames, fuzzy=fuzzy_firstname_match, score=score))
            else:
                log.info('No fuzzy first name match for {f1} and {f2}: {fuzzy}'
                          .format(f1=firstnames, f2=res_firstnames, fuzzy=fuzzy_firstname_match))

            if birth_place and res_birth_place and birth_place == res_birth_place:
                score += 30
            log.info('BPlace: {b} <-> {rb} -> {s}'.format(b=birth_place, rb=res_birth_place, s=score))

            if disappearance_place and res_disappearance_place and disappearance_place == res_disappearance_place:
                score += 25
            log.info('DPlace: {b} <-> {rb} -> {s}'.format(b=disappearance_place, rb=res_disappearance_place, s=score))

            if unit and res_unit and unit == res_unit:
                score += 15
            log.info('Unit: {b} <-> {rb} -> {s}'.format(b=unit, rb=res_unit, s=score))

            if occupation and res_occupation and occupation == res_occupation:
                score += 20
            log.info('Occupation: {b} <-> {rb} -> {s}'.format(b=occupation, rb=res_occupation, s=score))

            person['score'] = score

            rank_name = re.sub(r'.+/(\w+?)$', r'\1', str(rank))
            res_rank_name = ', '.join([re.sub(r'.+/(\w+?)$', r'\1', str(rank)) for rank in res_ranks])

            if score > 200:
                filtered.append(person)
                log.info('Found person for {rank} {fn} {ln} {uri} : '
                         '{res_rank} {res_fn} {res_ln} {res_uri} [score: {score}]'
                         .format(rank=rank_name, fn=s_first1, ln=lastname, uri=s, res_rank=res_rank_name, res_fn=s_first2,
                                 res_ln=res_lastname, res_uri=res_id, score=score))
            else:
                log.info('Skip low score [{score}]: {rank} {fn} {ln} {uri} <<-->> {res_rank} {res_fn} {res_ln} {res_uri}'
                         .format(rank=rank_name, fn=s_first1, ln=lastname, uri=s, res_rank=res_rank_name, res_fn=s_first2,
                                 res_ln=res_lastname, res_uri=res_id, score=score))

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
            SCHEMA_NS.warsa_rank, FOAF.givenName, FOAF.familyName,
            SCHEMA_NS.place_captured_municipality, SCHEMA_NS.time_captured,
            SCHEMA_NS.birth_place, SCHEMA_NS.warsa_unit, BIOC.has_occupation)
    arpa = ArpaMimic(get_query_template(), endpoint, retries=10, wait_between_tries=6)
    new_graph = process_graph(graph, CIDOC.P70_documents, arpa, progress=True,
                              validator=validator, new_graph=True, source_prop=SKOS.prefLabel)
    return new_graph['graph']


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="War prisoner linking tasks", fromfile_prefix_chars='@')

    argparser.add_argument("task", help="Linking task to perform", choices=["ranks", "persons"])
    argparser.add_argument("input", help="Input RDF file")
    argparser.add_argument("output", help="Output file location")
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    argparser.add_argument("--endpoint", default='http://localhost:3030/warsa/sparql', help="SPARQL Endpoint")

    args = argparser.parse_args()

    logging.basicConfig(filename='prisoners-{ts}.log'.format(ts=time.time()),
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
