#!/usr/bin/env python3
"""
Main entry point for bvsim_cli CLI module.
Handles command-line interface for high-level volleyball simulation functions.
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))