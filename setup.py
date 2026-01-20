#!/usr/bin/env python3
"""
Setup script for SkyWatcher Telescope Controller
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
readme_file = Path(__file__).parent / "README_FULL.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="skywatcher-controller",
    version="2.0.0",
    author="SkyWatcher Community",
    description="Professional telescope controller for SkyWatcher mounts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/skywatcher-pacific/skywatcher_open",
    py_modules=[
        "telescope_gui_v2",
        "telescope_control_v2"
    ],
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies!
        # tkinter is included with Python
    ],
    entry_points={
        'console_scripts': [
            'skywatcher-gui=telescope_gui_v2:main',
            'skywatcher-cli=telescope_control_v2:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "License :: OSI Approved :: MIT License",
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
