#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Converters for CSV cell data
"""

import datetime
import logging
import re

from rdflib import Graph, Literal
from slugify import slugify

from namespaces import *


log = logging.getLogger(__name__)


def convert_dates(raw_date: str):
    """
    Convert date string to iso8601 date

    :param raw_date: raw date string from the CSV
    :return: ISO 8601 compliant date if can be parse, otherwise original date string
    """
    error = None
    if not raw_date:
        return raw_date, None
    try:
        date = datetime.datetime.strptime(str(raw_date).strip(), '%d/%m/%Y').date()
        log.debug('Converted date: %s  to  %s' % (raw_date, date))
    except ValueError:
        try:
            date = datetime.datetime.strptime(str(raw_date).strip(), '%d.%m.%Y').date()
            log.debug('Converted date: %s  to  %s' % (raw_date, date))
        except ValueError:
            log.warning('Invalid value for date conversion: %s' % raw_date)
            if raw_date[:2] != 'xx':
                error = 'Päivämäärä ei ole kelvollinen'
            date = raw_date

    return date, error


def convert_person_name(raw_name: str):
    """
    Unify name syntax and split into first names and last name

    :param raw_name: Original name string
    :return: tuple containing first names, last name and full name
    """
    error = None
    re_name_split = \
        r'([A-ZÅÄÖÜÉÓÁ/\-]+(?:\s+\(?E(?:NT)?[\.\s]+[A-ZÅÄÖÜÉÓÁ/\-]+)?\)?)\s*(?:(VON))?,?\s*([A-ZÅÄÖÜÉÓÁ/\- \(\)0-9,.]*)'

    fullname = raw_name.upper()

    namematch = re.search(re_name_split, fullname)
    (lastname, extra, firstnames) = namematch.groups() if namematch else (fullname, None, '')

    # Unify syntax for previous names
    prev_name_regex = r'([A-ZÅÄÖÜÉÓÁ/\-]{2}) +\(?(E(?:NT)?[\.\s]+)([A-ZÅÄÖÜÉÓÁ/\-]+)\)?'
    lastname = re.sub(prev_name_regex, r'\1 (ent. \3)', str(lastname))

    lastname = lastname.title().replace('(Ent. ', '(ent. ')
    firstnames = firstnames.title()

    if extra:
        extra = extra.lower()
        lastname = ' '.join([extra, lastname])

    fullname = lastname

    if firstnames:
        fullname += ', ' + firstnames

    log.debug('Name %s was unified to form %s' % (raw_name, fullname))

    original_style_name = ' '.join((lastname, firstnames)) if firstnames else lastname
    if original_style_name.lower() != raw_name.lower():
        log.warning('New name %s differs from %s' % (original_style_name, raw_name))
        error = 'Tulkittu nimi [%s] poikkeaa alkuperäisestä' % original_style_name

    return firstnames, lastname, fullname, error


def create_event(uri_suffix, event_type, participant_prop, participant, participant_name, labels, timespan=None,
                 place=None, prop_sources=None, extra_information=None):
    """
    Create an event or add information to an existing one (by using a previously used URI).

    :param uri_suffix:
    :param event_type: URIRef
    :param participant_prop:
    :param participant:
    :param participant_name:
    :param labels: list of label literals in different languages
    :param timespan: timespan tuple (begin, end) or single date
    :param place: string representing the target place
    :param prop_sources:
    :param extra_information: list of (predicate, object) tuples
    """

    event = Graph()

    uri = EVENTS_NS[uri_suffix]
    event.add((uri, RDF.type, event_type))
    event.add((uri, participant_prop, participant))

    labels = (Literal(labels[0].format(name=participant_name), lang='fi'),
              Literal(labels[1].format(name=participant_name), lang='en'))

    for label in labels:
        event.add((uri, SKOS.prefLabel, label))

    # if event_source:
    #     event.add((uri, DC.source, event_source))

    if extra_information:
        for info in extra_information:
            event.add((uri,) + info)

    if timespan:
        if type(timespan) != tuple:
            timespan = (timespan, timespan)

        timespan_uri = EVENTS_NS[uri_suffix + '_timespan']
        label = (timespan[0] + ' - ' + timespan[1]) if timespan[0] != timespan[1] else timespan[0]

        event.add((uri, CIDOC['P4_has_time-span'], timespan_uri))
        event.add((timespan_uri, RDF.type, CIDOC['E52_Time-Span']))
        event.add((timespan_uri, CIDOC.P82a_begin_of_the_begin, Literal(timespan[0], datatype=XSD.date)))
        event.add((timespan_uri, CIDOC.P82b_end_of_the_end, Literal(timespan[1], datatype=XSD.date)))
        event.add((timespan_uri, SKOS.prefLabel, Literal(label)))

        if prop_sources:
            for timespan_source in prop_sources:
                event.add((timespan_uri, DC.source, timespan_source))

    if place:
        property_uri = CIDOC['P7_took_place_at']
        event.add((uri, property_uri, place))

        if prop_sources:
            # TODO: Use singleton properties or PROV Ontology (https://www.w3.org/TR/prov-o/#qualifiedAssociation)
            for place_source in prop_sources:
                # USING (SEMI-)SINGLETON PROPERTIES TO DENOTE SOURCE
                property_uri = DATA_NS['took_place_at_' + slugify(place) + '_' + slugify(place_source)]

                event.add((property_uri, DC.source, place_source))
                event.add((property_uri, RDFS.subClassOf, CIDOC['P7_took_place_at']))

    return event


def strip_dash(raw_value: str):
    return ('' if raw_value.strip() == '-' else raw_value), None

