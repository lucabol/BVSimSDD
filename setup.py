#!/usr/bin/env python3
"""
Setup script for BVSim - Beach Volleyball Point Simulator
"""

from setuptools import setup, find_packages
import os
import sys

# Add src to path to import version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from bvsim import __version__

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bvsim",
    version=__version__,
    author="BVSim Development Team",
    description="Beach Volleyball Point Simulator - A shot-by-shot simulator using conditional probability state machines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        "bvsim_web": ["static/**/*", "static/*"],
    },
    include_package_data=True,
    zip_safe=False,
)