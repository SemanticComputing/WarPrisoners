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

    import pprint
    pprint.pprint([firstnames, lastname, fullname, error])
    return firstnames, lastname, fullname, error


def strip_dash(raw_value: str):
    return ('' if raw_value.strip() == '-' else raw_value), None

