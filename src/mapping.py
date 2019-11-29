#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
CSV column mapping to RDF properties. Person name and person index number are taken separately.
"""
from datetime import date
from functools import partial

from rdflib import URIRef

from converters import convert_dates, strip_dash, convert_swedish, convert_from_dict
from namespaces import SCHEMA_POW, DCT, SCHEMA_WARSA, MARITAL_STATUSES

from validators import validate_dates, validate_mother_tongue

MARITAL_STATUS_MAP = {
    'asumuserossa': MARITAL_STATUSES.Naimisissa,
    'naimisissa': MARITAL_STATUSES.Naimisissa,
    'naimaton': MARITAL_STATUSES.Naimaton,
    'naimato': MARITAL_STATUSES.Naimaton,
    'eronnut': MARITAL_STATUSES.Eronnut,
    'leski': MARITAL_STATUSES.Leski,
    None: MARITAL_STATUSES.Tuntematon,
}


PRISONER_MAPPING = {
    'syntymäaika':
        {
            'uri': SCHEMA_WARSA.date_of_birth,
            'converter': convert_dates,
            'validator': partial(validate_dates, after=date(1860, 1, 1), before=date(1935, 1, 1)),
            'value_separator': '/',
            'name_fi': 'Syntymäpäivä',
            'name_en': 'Date of birth',
            'description_fi': 'Henkilön syntymäpäivä',
        },
    'synnyinkunta':
        {
            'uri': SCHEMA_WARSA.municipality_of_birth_literal,
            'value_separator': '/',
            'name_fi': 'Syntymäkunta',
            'name_en': 'Municipality of birth',
            'description_fi': 'Henkilön syntymäkunta',
        },
    'kotikunta':
        {
            'uri': SCHEMA_POW.municipality_of_domicile_literal,
            'value_separator': '/',
            'name_fi': 'Kotikunta',
            'name_en': 'Municipality of domicile',
            'description_fi': 'Kunta, jossa henkilö on ollut kirjoilla vangitsemishetkellä',
        },
    'asuinkunta':
        {
            'uri': SCHEMA_POW.municipality_of_residence_literal,
            'name_fi': 'Asuinkunta',
            'name_en': 'Municipality of residence',
            'value_separator': '/',
            'description_fi': 'Kunta, jossa henkilö on tosiasiassa asunut sotaan lähtiessä. Mikäli lähdettä ei ole '
                              'mainittu, ovat käytetyt lähteet tiedosta yksimielisiä tai on lähde on '
                              'Kansallisarkisto: Suomen sodissa 1939–1945 menehtyneiden tietokanta, KA T-26073/1, '
                              'KA T-26073/2–KA T-26073/22, KA T-26073/23, KA T-26073/24–KA-T 26073/47, KA T-26073/48, '
                              'KA T-26073/49, Kansallisarkisto kantakortit',
        },
    'kuolinkunta, palanneet':
        {
            'uri': SCHEMA_POW.municipality_of_death_literal,
            'name_en': 'Municipality of death',
            'name_fi': 'Kuolinkunta'
        },
    'ammatti':
        {
            'uri': SCHEMA_POW.occupation_literal,
            'name_fi': 'Ammatti',
            'name_en': 'Occupation',
            'value_separator': '/',
            'description_fi': 'Ammatti, jota henkilö on harjoittanut ennen vangitsemista. Mikäli lähdettä ei ole '
                              'mainittu, ovat käytetyt lähteet tiedosta yksimielisiä tai lähde on Kansallisarkisto: '
                              'Suomen sodissa 1939–1945 menehtyneiden tietokanta, KA T-26073/1, KA T-26073/2–KA '
                              'T-26073/22, KA T-26073/23, KA T-26073/24-KA T-26073/47, KA T-26073/48, KA T-26073/49, '
                              'Kansallisarkisto kantakortit',
        },
    'siviilisääty':
        {
            'uri': SCHEMA_POW.marital_status,
            'name_fi': 'Siviilisääty',
            'name_en': 'Marital status',
            'value_separator': '/',
            'description_fi': 'Henkilön tiedossa oleva siviilisääty vangitsemishetkellä. Mikäli lähdettä ei ole '
                              'mainittu, ovat käytetyt lähteet tiedosta yksimielisiä tai lähde on Kansallisarkisto: '
                              'Suomen sodissa 1939–1945 menehtyneiden tietokanta, KA T-26073/1, KA T-26073/2–KA '
                              'T-26073/22, KA T-26073/23, KA T-26073/24-KA T-26073/47, KA T-26073/48, KA-T 26073/49, '
                              'Kansallisarkisto kantakortit',
            'converter': partial(convert_from_dict, MARITAL_STATUS_MAP)
        },
    'lapset':
        {
            'uri': SCHEMA_POW.number_of_children,
            'converter': strip_dash,
            'name_fi': 'Lasten lukumäärä',
            'name_en': 'Number of children',
            'value_separator': '/',
            'description_fi': 'Henkilön lasten tiedossa oleva lukumäärä vangitsemishetkellä. Vankeuden jälkeen '
                              'syntyneistä lapsista ei ole kerätty tietoa. Mikäli lähdettä ei ole mainittu, ovat '
                              'käytetyt lähteet tiedosta yksimielisiä tai lähde on Kansallisarkisto: Suomen sodissa '
                              '1939–1945 menehtyneiden tietokanta',
        },
    'sotilasarvo':
        {
            'uri': SCHEMA_POW.rank_literal,
            'name_fi': 'Sotilasarvo',
            'name_en': 'Military rank',
            'value_separator': '/',
            'description_fi': 'Henkilön sotilasarvo vangitsemishetkellä. Mikäli lähdettä ei ole mainittu, ovat '
                              'käytetyt lähteet tiedosta yksimielisiä tai lähde on Kansallisarkisto: Suomen sodissa '
                              '1939–1945 menehtyneiden tietokanta, KA T-26073/1, KA T-26073/2–KA T-26073/22, KA '
                              'T-26073/23, KA T-26073/24-KA T-26073/47, KA T-26073/48, KA T-26073/49, Kansallisarkisto '
                              'kantakortit',
        },
    'joukko-osasto':
        {
            'uri': SCHEMA_POW.unit_literal,
            'name_en': 'Military unit',
            'name_fi': 'Joukko-osasto',
            'description_fi': 'Henkilön tiedossa oleva joukko-osasto vangitsemishetkellä',
        },
    'katoamisaika':
        {
            'uri': SCHEMA_POW.date_of_going_mia,
            'converter': convert_dates,
            'validator': validate_dates,
            'value_separator': '/',
            'name_en': 'Date of going missing in action',
            'name_fi': 'Katoamispäivä',
            'description_fi': 'Päivä, jona henkilö on suomalaisten lähteiden mukaan kadonnut. Päivämäärät ilmoitetaan '
                              'muodossa pp.kk.vvvv',
        },
    'katoamispaikka':
        {
            'uri': SCHEMA_POW.place_of_going_mia_literal,
            'value_separator': '/',
            'name_en': 'Place of going missing in action',
            'name_fi': 'Katoamispaikka',
            'description_fi': 'Paikka, jossa henkilö on suomalaisten lähteiden mukaan kadonnut',
        },
    'vangiksi aika':
        {
            'uri': SCHEMA_POW.date_of_capture,
            'converter': convert_dates,
            'validator': validate_dates,
            'value_separator': '/',
            'name_en': 'Date of capture',
            'name_fi': 'Vangiksi jäämisen päivämäärä',
            'description_fi': 'Päivä, jona henkilö on suomalaisten lähteiden mukaan kadonnut. Päivämäärät ilmoitetaan '
                              'muodossa pp.kk.vvvv',
        },
    'vangiksi paikka, kunta':
        {
            'uri': SCHEMA_POW.municipality_of_capture_literal,
            'value_separator': '/',
            'name_en': 'Municipality of capture',
            'name_fi': 'Vangiksi jäämisen kunta',
            'description_fi': 'Kunta, jonka alueella henkilö on jäänyt sotavangiksi. Mikäli lähdettä ei ole mainittu, '
                              'ovat käytetyt lähteet tiedosta yksimielisiä tai lähde on KA T-26073/1, KA T-26073/2–KA '
                              'T-26073/22, KA T-26073/23, KA T-26073/24-KA T-26073/47, KA T-26073/48, KA T-26073/49, '
                              'Kansallisarkisto kantakortit',
        },
    'vangiksi paikka, kylä, kaupunginosa':
        {
            'uri': SCHEMA_POW.place_of_capture_literal,
            'value_separator': '/',
            'name_en': 'Village or district of capture',
            'name_fi': 'Vangiksi jäämisen kylä tai kaupunginosa',
            'description_fi': 'Kylä tai kaupunginosa, jossa henkilö on jäänyt sotavangiksi. Mikäli lähdettä ei ole '
                              'mainittu, ovat käytetyt lähteet tiedosta yksimielisiä tai lähde on KA T-26073/1, '
                              'KA T-26073/2–KA T-26073/22, KA T-26073/23, KA T-26073/24-KA T-26073/47, KA T-26073/48, '
                              'KA T-26073/49, Kansallisarkisto kantakortit',
        },
    'vangiksi taistelupaikka':
        {
            'uri': SCHEMA_POW.place_of_capture_battle_literal,
            'value_separator': '/',
            'name_en': 'Location of battle in which captured',
            'name_fi': 'Vangiksi jäämisen taistelupaikka'
        },
    'vangiksi jääminen, oma tai muiden selostus kuulusteluissa, arkistotietoja':
        {
            'uri': SCHEMA_POW.description_of_capture,
            'value_separator': ';',
            'name_en': 'Description of capture',
            'name_fi': 'Selvitys vangiksi jäämisestä',
            'description_fi': 'Tieto siitä, miten henkilö on jäänyt vangiksi joko hänen oman kertomansa tai muun '
                              'lähteen mukaan. Lähteinä ilman erillistä merkintää KA T-26073/1, KA T-26073/2–KA '
                              'T-26073/22, KA T-26073/23, KA T-26073/24-KA T-26073/47, KA T-26073/48, KA T-26073/49, '
                              'Kansallisarkisto kantakortit',
        },
    'palannut':
        {
            'uri': SCHEMA_POW.date_of_return,
            'converter': convert_dates,
            'validator': partial(validate_dates, after=date(1939, 11, 30), before=date(1980, 1, 1)),
            'value_separator': '/',
            'name_en': 'Date of return from captivity',
            'name_fi': 'Sotavankeudesta palaamisen päivämäärä',
            'description_fi': 'Päivä, jona henkilö on palannut Suomeen sotavankeudesta'
        },
    'kuollut':
        {
            'uri': SCHEMA_POW.date_of_death,
            'converter': convert_dates,
            'validator': partial(validate_dates, after=date(1939, 11, 30), before=date.today()),
            'value_separator': '/',
            'name_en': 'Date of death',
            'name_fi': 'Kuolinpäivä',
            'description_fi': 'Henkilön tiedossa oleva kuolinpäivä. Mikäli lähdettä ei ole mainittu, ovat käytetyt '
                              'lähteet tiedosta yksimielisiä tai lähde on Kansallisarkisto: '
                              'Suomen sodissa 1939–1945 menehtyneiden tietokanta.',
        },
    'kuolinsyy':
        {
            'uri': SCHEMA_POW.cause_of_death,
            'value_separator': '/',
            'name_en': 'Cause of death',
            'name_fi': 'Kuolinsyy'
        },
    'kuolinpaikka':
        {
            'uri': SCHEMA_POW.place_of_death,
            'value_separator': '/',
            'name_en': 'Place of death',
            'name_fi': 'Kuolinpaikka',
            'description_fi': 'Sotavankeuden jälkeen kuolleen henkilön kuolinpaikka. Jollei lähdettä ole erikseen '
                              'mainittu, on lähde Väestörekisterikeskuksen Väestötietojärjestelmä (VTJ)',
        },
    'hautauspaikka ja -aika':
        {
            'uri': SCHEMA_POW.place_of_burial_literal,
            'value_separator': ';',
            'name_en': 'Place of burial',
            'name_fi': 'Hautauspaikka'
        },
    'vankeuspaikat':
        {
            'uri': SCHEMA_POW.captivity,
            'value_separator': ';',
            'create_resource': SCHEMA_POW.Captivity,
            'capture_value': SCHEMA_POW.location_literal,
            'capture_order_number': True,
            'capture_dates': True,
            'create_resource_label_fi': 'Henkilön {person} sotavankeus',
            'create_resource_label_en': 'Person\'s {person} captivity',
            'name_en': 'Captivity locations',
            'name_fi': 'Vankeuspaikat',
            'description_fi': 'Ne kuulustelupaikat, vankileirit, vankilat ja sairaalat, joissa vanki on eri lähteistä '
                              'saatujen tietojen mukaan ollut sotavankeusaikanaan sekä kussakin paikassa oleskelun '
                              'päivämäärät.  Leirin tai sairaalan numeroa klikkaamalla näet sen tiedossa olevan '
                              'sijainnin ja mahdolliset muut tiedot. Mikäli vankeuspaikkamerkintää ei voi klikata, on '
                              'se tuntematon (esim. tiedossa on vankeuspaikan paikkakunta, mutta ei virallista numeroa '
                              'tai nimeä)',
        },
    'muita tietoja':
        {
            'uri': SCHEMA_POW.additional_information,
            'value_separator': ';',
            'name_fi': 'Muita vankeustietoja',
            'name_en': 'Additional information',
            'description_fi': 'Muita sotavankeuteen liittyviä tietoja',
        },
    'palanneiden kuolinaika':
        {
            'uri': SCHEMA_POW.date_of_death,
            'converter': convert_dates,
            'validator': partial(validate_dates, after=date(1939, 11, 30), before=date.today()),
            'value_separator': '/'
        },
    'kuolleeksi julistaminen':
        {
            'uri': SCHEMA_POW.date_of_declaration_of_death,
            'converter': convert_dates,
            'validator': partial(validate_dates, after=date(1939, 11, 30), before=date.today()),
            'name_en': 'Date of declaration of death',
            'name_fi': 'Kuolleeksi julistamisen päivämäärä'
        },
    'valokuva KA:n henkilöakteissa, RGVA:n henkilömapeissa, muissa venäläisissä arkistoissa ja suomalaisissa julkaisuissa':
        {
            'uri': SCHEMA_POW.photograph,
            'value_separator': ';',
            'name_fi': 'Valokuva',
            'name_en': 'Photograph'
        },
    'valokuva Sotilaan Äänessä':
        {
            'uri': SCHEMA_POW.photograph_sotilaan_aani,
            'value_separator': ';',
            'name_fi': 'Valokuva Sotilaan Ääni -lehdessä',
            'name_en': 'Photograph in Sotilaan Ääni magazine'
        },
    'suomalainen paluukuulustelupöytäkirja':
        {
            'uri': SCHEMA_POW.finnish_return_interrogation_file,
            'value_separator': ';',
            'name_en': 'Finnish return interrogation file',
            'name_fi': 'Suomalainen paluukuulustelupöytäkirja'
        },
    'radiossa, PM:n valvontatoimiston radiokatsaukset':
        {
            'uri': SCHEMA_POW.radio_report,
            'value_separator': ';',
            'name_en': 'Radio reports',
            'name_fi': 'PM:n valvontatoimiston radiokatsaukset',
            'description_fi': 'Neuvostoliitto lähetti suomenkielisiä propagandalähetyksiä sekä talvi- että jatkosodan '
                              'aikana, enimmillään 14 lähetystä päivässä. Lähetysasemat sijaitsivat Leningradissa, '
                              'Moskovassa, Petroskoissa, Karhumäessä ja Sorokassa (Belomorsk). Kadonneiden omaisille '
                              'radiolähetykset olivat tärkeitä siksi, että niissä luettiin sotavankien kirjeitä ja '
                              'terveisiä omaisilleen sekä varsinkin kesällä 1944 vankeuteen joutuneiden luetteloja. '
                              'Joskus lähetettiin myös leireillä levytettyjä haastatteluja. Suomessa lähetysten '
                              'kuuntelu oli Päämajan valvontatoimiston tehtävänä. Valvontatoimisto laati '
                              'sotavankinimistä luetteloja jo seuraavaksi päiväksi, viikonlopun jälkeen ensimmäiseksi '
                              'arkipäiväksi.',
        },
    'vankeudessa takavarikoitu omaisuus markoissa':
        {
            'uri': SCHEMA_POW.confiscated_possession,
            'name_en': 'Confiscated possessions',
            'name_fi': 'Vankeudessa takavarikoitu omaisuus markoissa',
            'description_fi': 'Jatkosodan toisen (25.12.1944) ja kolmannen (28.3.1945) palautuserän sotavangeille '
                              'tehty erillinen kysymys. Lähteinä KA T-26073/2–KA T-26073/22',
        },
    'suomenruotsalainen':
        {
            'uri': SCHEMA_WARSA.mother_tongue,
            'converter': convert_swedish,
            'validator': validate_mother_tongue,
            'name_en': 'Mother tongue',
            'name_fi': 'Äidinkieli'
        },
    'Karagandan kortisto':
        {
            'uri': SCHEMA_POW.karaganda_card_file,
            'value_separator': ';',
            'name_en': 'Karaganda card file',
            'name_fi': 'Karagandan kortisto'
        },
    'Neuvostoliittolaiset sotavankikortistot ja henkilömappikokoelmat':
        {
            'uri': SCHEMA_POW.soviet_card_files,
            'value_separator': ';',
            'name_en': 'Soviet prisoner of war card files and person registers',
            'name_fi': 'Neuvostoliittolaiset sotavankikortistot ja henkilömappikokoelmat',
            'desciption_fi': 'Talvisodan kortisto, Jatkosodan kortisto, Palautettujen henkilömapit, Sotavankeudessa '
                             'kuolleiden henkilömapit, Vangittujen ja internoitujen henkilömapit. Mikäli korttien tai '
                             'mappien lukumäärää ei ole mainittu, on kyseisessä kokoelmassa yksi vankia koskeva '
                             'kortti tai mappi. Mikäli henkilömapin sisältöä ei ole lueteltu, sisältää mappi vain ns. '
                             'kuulustelulomakkeen. Kokoelmia voi selata Digitaaliarkistossa Kansallisarkiston '
                             'toimipisteiden yleisöpäätteillä, haku vangin nimellä. Vangittujen ja internoitujen '
                             'henkilömappien selailu vaatii erillisen luvan hakemista. Asiakirjat ovat pääosin '
                             'venäjänkielisiä.',
        },
    'Talvisodan kokoelma':
        {
            'uri': SCHEMA_POW.winter_war_collection,
            'value_separator': ';',
            'name_en': 'Winter War collection',
            'name_fi': 'Talvisodan kokoelma',
            'description_fi': 'Venäjän valtion sota-arkisto RGVA, Fondi 34980 Talvisodan kokoelma. '
                              'Neuvostoliittolaisia talvisotaa koskevia asiakirjoja, jotka ovat selattavissa '
                              'Digitaaliarkistossa Kansallisarkiston toimipisteiden yleisöpäätteillä. Asiakirjan '
                              'hakuohje: tee Digitaaliarkiston etusivulla Aineiston haku esim. sanoilla ’talvisodan '
                              'kokoelma’ -> klikkaa linkkiä ’RGVA Fondi 34980 Talvisodan kokoelma’ -> klikkaa '
                              '’asiakirjat’ -> valitse avautuvan sivun ylälaidasta ’kaikki’ -> tee haku sivulta '
                              'painamalla ensin ctrl + f ja kirjoita hakuruutuun hakemasi arkistoyksikön numerotunnus '
                              'muotoa x:xxx (tunnuksia on eripituisia) -> klikkaa oikeaa arkistoyksikköä, '
                              'jolloin pääset selaamaan ko. kansiossa olevia asiakirjoja.',
        },
    'lentolehtinen':
        {
            'uri': SCHEMA_POW.flyer,
            'value_separator': ';',
            'name_en': 'Flyer',
            'name_fi': 'Lentolehtinen',
            'description_fi': 'Neuvostoliittolaiset propagandalentolehtiset, joissa henkilö on mainittu',
        },
    'Sotilaan Ääni-lehti, digitoitu ja indeksoitu':
        {
            'uri': SCHEMA_POW.sotilaan_aani,
            'value_separator': ';',
            'name_en': 'Sotilaan Ääni magazine',
            'name_fi': 'Sotilaan Ääni'
        },
    'Kansan Valta, Kansan Mies, Kansan Ääni, Suomen Kansan Ääni, Kansan Sana':
        {
            'uri': SCHEMA_POW.propaganda_magazine,
            'value_separator': ';',
            'name_en': 'Propaganda magazine',
            'name_fi': 'Propagandalehti',
            'description_fi': 'Neuvostoliittolaiset suomen- ja venäjänkieliset propagandalehdet (pl. Sotilaan Ääni), '
                              'joissa henkilö on mainittu.',
        },
    'Kansan Valta, Kansan Mies, Kansan Ääni, Suomen Kansan Ääni. Linkit':
        {
            'uri': SCHEMA_POW.propaganda_magazine_link,
            'converter': URIRef,
            'value_separator': ';',
            'name_en': 'Propaganda magazine link',
            'name_fi': 'Linkki propagandalehteen',
        },
    'Kansan Valta, Kansan Mies, Kansan Ääni, Suomen Kansan Ääni. Toiset linkit':
        {
            'uri': SCHEMA_POW.propaganda_magazine_link,
            'converter': URIRef,
            'value_separator': ';',
            'name_en': 'Propaganda magazine link',
            'name_fi': 'Linkki propagandalehteen',
        },
    'Kansan Valta, Kansan Mies, Kansan Ääni, Suomen Kansan Ääni. Kolmannet linkit':
        {
            'uri': SCHEMA_POW.propaganda_magazine_link,
            'converter': URIRef,
            'value_separator': ';',
            'name_en': 'Propaganda magazine link',
            'name_fi': 'Linkki propagandalehteen',
        },
    'Kansan Valta, Kansan Mies, Kansan Ääni, Suomen Kansan Ääni. Neljännet linkit':
        {
            'uri': SCHEMA_POW.propaganda_magazine_link,
            'converter': URIRef,
            'value_separator': ';',
            'name_en': 'Propaganda magazine link',
            'name_fi': 'Linkki propagandalehteen',
        },
    'muistelmat, lehtijutut, tietokirjat, tutkimukset, Kansa taisteli-lehti, näyttelyt':
        {
            'uri': SCHEMA_POW.memoir,
            'value_separator': ';',
            'name_en': 'Memoirs',
            'name_fi': 'Muistelmat, lehtiartikkelit ja kirjallisuus',
            'description_fi': 'Kirjallisissa lähteissä olevat maininnat henkilön sotavankeudesta',
        },
    'TV-ja radio-ohjelmat, tallenne video/audio':
        {
            'uri': SCHEMA_POW.recording,
            'name_en': 'Recording (video/audio)',
            'name_fi': 'Tallenne (video/audio)'
        },
    'Karjalan tasavallan kansallisarkiston dokumentit':
        {
            'uri': SCHEMA_POW.karelian_archive_documents,
            'name_en': 'Karelian archive documents',
            'name_fi': 'Karjalan kansallisarkiston dokumentit'
        },
}

SOURCE_MAPPING = {
    'Merkintä':
        {
            'uri': SCHEMA_POW.source_id,
            'name_en': 'Source identifier',
            'name_fi': 'Lähteen tunniste',
        },
    'Selitys':
        {
            'uri': DCT.description,
        },
}
