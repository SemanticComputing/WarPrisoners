#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Get all data sources.
"""
import argparse

from rdflib import Graph, URIRef


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument("input", help="Input file")
    args = argparser.parse_args()

    g = Graph()
    g.parse(args.input, format='turtle')
    sources = list(g.objects(None, URIRef('http://purl.org/dc/terms/source')))
    for source in sorted(set(s.value for s in sources)):
        print(source)
