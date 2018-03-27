#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Define common RDF namespaces
"""
from rdflib import Namespace, RDF, RDFS, XSD

CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/terms/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')

DATA_NS = Namespace('http://ldf.fi/warsa/prisoners/')
SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/prisoners/')
WARSA_NS = Namespace('http://ldf.fi/schema/warsa/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')


def bind_namespaces(graph):
    graph.bind("p", "http://ldf.fi/warsa/prisoners/")
    graph.bind("ps", "http://ldf.fi/schema/warsa/prisoners/")
    graph.bind("skos", "http://www.w3.org/2004/02/skos/core#")
    graph.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
    graph.bind("bioc", 'http://ldf.fi/schema/bioc/')
    graph.bind("dct", 'http://purl.org/dc/terms/')

