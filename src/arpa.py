#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""Local wrapper for arpa-linker command line usage"""

import sys

from arpa_linker.arpa import main


if __name__ == '__main__':
    main(sys.argv[1:])  # Run arpa-linker main

