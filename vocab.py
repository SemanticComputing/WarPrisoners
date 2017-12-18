#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""Local wrapper for CSV2RDF vocab_literals command line usage"""
import logging
import sys

from csv2rdf.vocab_literals import main


if __name__ == '__main__':
    logging.basicConfig(filename='prisoners.log', filemode='a', level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    main(sys.argv)
