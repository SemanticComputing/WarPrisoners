#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Get all data sources.
"""
from rdflib import Graph, URIRef

g = Graph()
g.parse('data/new/prisoners.ttl', format='turtle')
sources = list(g.objects(None, URIRef('http://purl.org/dc/terms/source')))
for source in sorted(set(s.value for s in sources)):
    print(source)
