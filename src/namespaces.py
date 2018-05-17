#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Define common RDF namespaces
"""
from rdflib import Namespace, RDF, RDFS, XSD, Graph

CRM = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DCT = Namespace('http://purl.org/dc/terms/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
WARSA_NS = Namespace('http://ldf.fi/schema/warsa/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')

ACTORS = Namespace('http://ldf.fi/warsa/actors/')
SCHEMA_ACTORS = Namespace('http://ldf.fi/schema/warsa/actors/')


def bind_namespaces(graph: Graph):
    graph.bind("wp", "http://ldf.fi/warsa/prisoners/")
    graph.bind("wps", "http://ldf.fi/schema/warsa/prisoners/")
    graph.bind("bioc", BIOC)
    graph.bind("dct", DCT)
    graph.bind("crm", CRM)
    graph.bind("skos", SKOS)
    graph.bind("foaf", FOAF)

    graph.bind("wsch", WARSA_NS)
    graph.bind("wac", ACTORS)

    return graph
