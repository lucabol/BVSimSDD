#!/usr/bin/env python3
"""
Main entry point for bvsim_core CLI module.
Handles command-line interface for core volleyball simulation functions.
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))