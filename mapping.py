#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Mapping of CSV columns to RDF properties
"""

from rdflib import Namespace

from converters import convert_dates

CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/elements/1.1/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')

# Mapping dict. Person name is taken from the first field separately.

PRISONER_MAPPING = {
    'syntymäaika': {'uri': SCHEMA_NS.birth_date,
                    'converter': convert_dates,
                    'value_separator': '/',
                    'name_fi': 'Syntymäaika',
                    'name_en': 'Date of birth'},
    'syntymäpaikka': {'uri': SCHEMA_NS.birth_place,
                      'value_separator': '/',
                      'name_fi': 'Syntymäkunta',
                      'name_en': 'Municipality of birth'
                      },
    'kotipaikka': {'uri': SCHEMA_NS.home_place,
                   'value_separator': '/',
                   'name_fi': 'Kotikunta',
                   'name_en': 'Home municipality'
                   },
    'asuinpaikka': {'uri': SCHEMA_NS.residence_place,
                    'name_fi': 'Asuinpaikka',
                    'value_separator': '/'},
    'ammatti': {'uri': BIOC.has_occupation,
                'name_fi': 'Ammatti',
                'value_separator': '/'},
    'siviilisääty': {'uri': SCHEMA_NS.marital_status,
                     'name_fi': 'Siviilisääty',
                     'value_separator': '/'},
    'lasten lkm': {'uri': SCHEMA_NS.amount_children,
                   'name_fi': 'Lasten lukumäärä',
                   'value_separator': '/'},
    'sotilasarvo': {'uri': SCHEMA_NS.rank,
                      'name_fi': 'Sotilasarvo',
                      'value_separator': '/'},
    'joukko-osasto': {'uri': SCHEMA_NS.unit,
                      'name_fi': 'Joukko-osasto'},
    'vangiksi aika': {'uri': SCHEMA_NS.time_captured,
                      'converter': convert_dates,
                      'value_separator': '/',
                      'name_fi': 'Vangiksi jäämisen päivämäärä'},
    'vangiksi paikka, kunta': {'uri': SCHEMA_NS.place_captured_municipality,
                               'value_separator': '/',
                               'name_fi': 'Vangiksi jäämisen kunta'},
    'vangiksi paikka, kylä, kaupunginosa': {'uri': SCHEMA_NS.place_captured,
                                            'value_separator': '/',
                                            'name_fi': 'Vangiksi jäämisen paikka'},
    'vangiksi, taistelupaikka': {'uri': SCHEMA_NS.place_captured_battle,
                                 'value_separator': '/',
                                 'name_fi': 'Vangiksi jäämisen taistelupaikka'},
    'selvitys vangiksi jäämisestä': {'uri': SCHEMA_NS.explanation,
                                     'name_fi': 'Selvitys vangiksi jäämisestä'},
    'palannut': {'uri': SCHEMA_NS.returned_date,
                 'converter': convert_dates,
                 'value_separator': '/',
                 'name_fi': 'Palaamisaika'},
    'kuollut': {'uri': SCHEMA_NS.death_date,
                'converter': convert_dates,
                'value_separator': '/',
                'name_fi': 'Kuolinaika'},
    'kuolinsyy': {'uri': SCHEMA_NS.cause_of_death,
                  'name_fi': 'Kuolinsyy'},
    'kuolinpaikka': {'uri': SCHEMA_NS.death_place,  # epämääräinen muotoilu
                     'value_separator': '/',
                     'name_fi': 'kuolinpaikka'},
    'hautauspaikka': {'uri': SCHEMA_NS.burial_place,
                      'value_separator': ';',
                      'name_fi': 'Hautauspaikka'},
    'leirit / sairaalat': {'uri': SCHEMA_NS.camps_and_hospitals,
                           'value_separator': ';',
                           'name_fi': 'Leirit ja sairaalat'},
    ' muita tietoja': {'uri': SCHEMA_NS.other_information,
                       'value_separator': ';',
                       'name_fi': 'Muita tietoja',
                       },
    'lisätietoja': {'uri': SCHEMA_NS.additional_information,
                    'value_separator': ';',
                    'name_fi': 'Lisätietoja'},
    'palanneiden kuolinaika': {'uri': SCHEMA_NS.death_date_of_returned,
                               'value_separator': '/',
                               'converter': convert_dates,
                               'name_fi': 'Palanneen kuolinaika'},
    'Sotavangit ry:n jäsen': {'uri': SCHEMA_NS.workspace, 'value_separator': '/',
                              'name_fi': 'Sotavangit ry:n jäsen'},
    'valokuva': {'uri': SCHEMA_NS.photograph, 'name_fi': 'Valokuva'},
    'paluukuulustelu-pöytäkirja; kjan lausunto; ilmoitus jääneistä sotavangeista':
        {'uri': SCHEMA_NS.minutes, 'value_separator': '/',
         'name_fi': 'Paluukuulustelu-pöytäkirja, kjan lausunto, sivumäärä'},
    'kantakortti': {'uri': SCHEMA_NS.military_record,
                    'name_fi': 'Kantakortti'},
    'radiokatsaus': {'uri': SCHEMA_NS.radio_report,
                     'value_separator': ';',
                     'name_fi': 'Radiokatsaus'},
    'katoamis-dokumentit': {'uri': SCHEMA_NS.missing_person_documents,
                            'name_fi': 'Katoamisdokumentit'},
    'Jatkosodan VEN kuulustelulomakkeet, palautetut': {'uri': SCHEMA_NS.russian_interrogation_sheets,
                                                       'value_separator': ';',
                                                       'name_fi': 'Jatkosodan venäläiset kuulustelulomakkeet'},
    'Talvisodan kortisto': {'uri': SCHEMA_NS.winterwar_card_file,
                            'name_fi': 'Talvisodan kortisto'},
    'kuulustelija': {'uri': SCHEMA_NS.interrogator,
                     'value_separator': ';',
                     'name_fi': 'Kuulustelija'},
    'takavarikoitu omaisuus, arvo markoissa':
        {'uri': SCHEMA_NS.confiscated_possessions,
         'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
    'suomenruotsalainen':
        {'uri': SCHEMA_NS.swedish_finn,
         'name_fi': 'takavarikoitu omaisuus, arvo markoissa'},
    'Karagandan kortisto':
        {'uri': SCHEMA_NS.karaganda_card_file,
         'name_fi': 'Karagandan kortisto'},
    'Jatkosodan kortisto':
        {'uri': SCHEMA_NS.continuation_war_card_file,
         'name_fi': 'Jatkosodan kortisto'},
    'Jatkosodan VEN kuulustelulomakkeet, kuolleet':
        {'uri': SCHEMA_NS.continuation_war_russian_card_file,
         'name_fi': 'Kuolleiden Jatkosodan venäläiset kuulustelulomakkeet'},
    'Talvisodan kokoelma':
        {'uri': SCHEMA_NS.winter_war_collection,
         'name_fi': 'Talvisodan kokoelma'},
    'Talvisodan kokoelma, Moskovasta tulevat':
        {'uri': SCHEMA_NS.winter_war_collection_from_moscow,
         'value_separator': ';',
         'name_fi': 'Talvisodan kokoelma (Moskovasta)'},
    'lentolehtinen':
        {'uri': SCHEMA_NS.flyer,
         'value_separator': ';',
         'name_fi': 'Lentolehtinen'},
    'muistelmat, lehtijutut':
        {'uri': SCHEMA_NS.memoirs,
         'name_fi': 'Muistelmat ja lehtijutut'},
    'tallenne video/audio':
        {'uri': SCHEMA_NS.recording,
         'name_fi': 'Tallenne (video/audio)'},
    'Karjalan kansallisarkiston dokumentit':
        {'uri': SCHEMA_NS.karelian_archive_documents,
         'name_fi': 'Karjalan kansallisarkiston dokumentit'},
}
