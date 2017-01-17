#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Mapping of CSV columns to RDF properties
"""

from rdflib import Namespace, Literal

from converters import *

CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/elements/1.1/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')

PRISONER_MAPPING = {
    'syntymäaika': {'uri': SCHEMA_NS.birth_date, 'converter': convert_dates, 'slash_separated': True,
                    'name_fi': 'Syntymäaika',
                    'name_en': 'Date of birth'},
    'syntymäpaikka': {'uri': SCHEMA_NS.birth_place, 'slash_separated': True,
                      'name_fi': 'Syntymäkunta',
                      'name_en': 'Municipality of birth'
                      },
    'kotipaikka': {'uri': SCHEMA_NS.home_place, 'slash_separated': True,
                   'name_fi': 'Kotikunta',
                   'name_en': 'Home municipality'
                   },
    'asuinpaikka': {'uri': SCHEMA_NS.residence_place, 'name_fi': 'Asuinpaikka', 'slash_separated': True},
    'ammatti': {'uri': BIOC.has_profession, 'name_fi': 'Ammatti', 'slash_separated': True},
    'siviilisääty': {'uri': SCHEMA_NS.marital_status, 'name_fi': 'Siviilisääty', 'slash_separated': True},
    'lasten lkm': {'uri': SCHEMA_NS.amount_children,
                   'name_fi': 'Lasten lukumäärä', 'slash_separated': True},
    'sotilas- arvo': {'uri': SCHEMA_NS.rank, 'name_fi': 'Sotilasarvo', 'slash_separated': True},
    '2': {'uri': SCHEMA_NS.unit, 'name_fi': 'Joukko-osasto', 'slash_separated': False},
    'vangiksi aika': {'uri': SCHEMA_NS.time_captured, 'converter': convert_dates, 'slash_separated': True,
                      'name_fi': 'Vangiksi jäämisen päivämäärä'},
    'vangiksi paikka': {'uri': SCHEMA_NS.place_captured, 'slash_separated': True,
                        'name_fi': 'Vangiksi jäämisen paikka'},
    'selvitys vangiksi jäämisestä': {'uri': SCHEMA_NS.explanation, 'slash_separated': False,
                                     'name_fi': 'Selvitys vangiksi jäämisestä'},
    'palannut': {'uri': SCHEMA_NS.returned_date, 'converter': convert_dates, 'slash_separated': True,
                 'name_fi': 'Palaamisaika'},
    'kuollut': {'uri': SCHEMA_NS.death_date, 'converter': convert_dates, 'slash_separated': True,
                'name_fi': 'Kuolinaika'},
    'kuolinsyy': {'uri': SCHEMA_NS.cause_of_death, 'slash_separated': False,
                  'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'uri': SCHEMA_NS.death_place, 'slash_separated': False,  # epämääräinen muotoilu
                     'name_fi': 'kuolinpaikka'},
    'hautauspaikka': {'uri': SCHEMA_NS.burial_place, 'slash_separated': False, 'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': SCHEMA_NS.camps_and_hospitals, 'slash_separated': False,
                           'name_fi': 'Leirit ja sairaalat'},
    ' muita tietoja': {'uri': SCHEMA_NS.other_information, 'slash_separated': False,
                       'name_fi': 'Muita tietoja',
                       },
    'lisätietoja': {'uri': SCHEMA_NS.additional_information, 'slash_separated': False,
                    'name_fi': 'Lisätietoja'},
    'palanneiden kuolinaika': {'uri': SCHEMA_NS.death_date_of_returned, 'converter': convert_dates,
                               'slash_separated': False,
                               'name_fi': 'Palanneen kuolinaika'},
    'Sotavangit ry:n jäsen': {'uri': SCHEMA_NS.workspace, 'slash_separated': True,
                              'name_fi': 'Sotavangit ry:n jäsen'},
    'valokuva': {'uri': SCHEMA_NS.photograph, 'slash_separated': False, 'name_fi': 'Valokuva'},
    'paluukuulustelu-pöytäkirja; kjan lausunto; ilmoitus jääneistä sotavangeista; yht. sivumäärä':
        {'uri': SCHEMA_NS.minutes, 'slash_separated': True,
         'name_fi': 'Paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä'},
    'kantakortti': {'uri': SCHEMA_NS.military_record, 'slash_separated': False, 'name_fi': 'Kantakortti'},
    'radiokatsaus': {'uri': SCHEMA_NS.radio_report, 'slash_separated': False, 'name_fi': 'Radiokatsaus'},
    'katoamis-dokumentit': {'uri': SCHEMA_NS.missing_person_documents, 'slash_separated': False,
                            'name_fi': 'Katoamisdokumentit'},
    'kuulustelija': {'uri': SCHEMA_NS.interrogator, 'slash_separated': False, 'name_fi': 'Kuulustelija'},
    'takavarikoitu omaisuus, arvo markoissa':
        {'uri': SCHEMA_NS.confiscated_possessions, 'slash_separated': True,
         'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
    'suomenruotsalainen':
        {'uri': SCHEMA_NS.confiscated_possessions, 'slash_separated': True,
         'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
}
