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
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Games/Entertainment :: Simulation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=5.1",
    ],
    entry_points={
        "console_scripts": [
            "bvsim=bvsim.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)