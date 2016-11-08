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
    'syntymäaika': {'converter': convert_dates,
                    'slash_separated': True,
                    'event': CIDOC.E67_Birth,
                    'event_prop': 'timespan',
                    'participant_prop': CIDOC.P98_brought_into_life,
                    'event_uri_suffix': '_birth',
                    'event_labels': ('Henkilö {name} syntyi', 'Person {name} was born'),
                    },
    'syntymäpaikka': {'converter': Literal,
                      'slash_separated': True,
                      'event': CIDOC.E67_Birth,
                      'event_prop': 'place',
                      'participant_prop': CIDOC.P98_brought_into_life,
                      'event_uri_suffix': '_birth',
                      'event_labels': ('Henkilö {name} syntyi', 'Person {name} was born'),
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
    'kuollut': {'converter': convert_dates,
                'slash_separated': True,
                'event': CIDOC.E69_Death,
                'event_prop': 'timespan',
                'participant_prop': CIDOC.P100_was_death_of,
                'event_uri_suffix': '_death',
                'event_labels': ('Henkilö {name} kuoli', 'Person {name} died'),
                },
    'kuolinsyy': {'uri': SCHEMA_NS.cause_of_death, 'slash_separated': False,
                  'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'slash_separated': False,  # epämääräinen muotoilu
                     'converter': Literal,
                     'event': CIDOC.E69_Death,
                     'event_prop': 'place',
                     'participant_prop': CIDOC.P100_was_death_of,
                     'event_uri_suffix': '_death',
                     'event_labels': ('Henkilö {name} kuoli', 'Person {name} died'),
                     },
    'hautauspaikka': {'uri': SCHEMA_NS.burial_place, 'slash_separated': False, 'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': SCHEMA_NS.camps_and_hospitals, 'slash_separated': False,
                           'name_fi': 'Leirit ja sairaalat'},
    ' muita tietoja': {'uri': SCHEMA_NS.other_information, 'slash_separated': False,
                       'name_fi': 'Muita tietoja',
                       },
    'lisätietoja': {'uri': SCHEMA_NS.additional_information, 'slash_separated': False,
                    'name_fi': 'Lisätietoja'},
    'palanneiden kuolinaika': {'converter': convert_dates,
                               'slash_separated': True,
                               'event': CIDOC.E69_Death,
                               'event_prop': 'timespan',
                               'participant_prop': CIDOC.P100_was_death_of,
                               'event_uri_suffix': '_death',
                               'event_labels': ('Henkilö {name} kuoli', 'Person {name} died'),
                               },
    'Sotavangit ry:n jäsen': {'converter': convert_dates,
                              'slash_separated': True,
                              'event': CIDOC.E85_Joining,
                              'event_prop': 'timespan',
                              'participant_prop': CIDOC.P143_joined,
                              'event_uri_suffix': '_prisoner_association',
                              'event_information': [(CIDOC.P144_joined_with, DATA_NS.Prisoner_association)],
                              'event_labels': ('Henkilö {name} liittyi ryhmään', 'Person {name} joined group'),
                              },
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
