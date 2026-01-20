#!/usr/bin/env python3
"""
Setup script for SkyWatcher Telescope Controller
"""

from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="star-command",
    version="2.0.0",
    author="Seth Stuart",
    description="Python based telescope controller for SkyWatcher GTi dobsonian mounts",
    url="https://github.com/sethstuart/starcommand/",
    py_modules=[
        "StarCommandGUI",
        "StarCommandCLI"
    ],
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies!
        # tkinter is included with Python
    ],
    entry_points={
        'console_scripts': [
            'starcommand=StarCommandGUI:main',
            'starcommand-cli=StarCommandCLI:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="telescope astronomy skywatcher mount control",
)
