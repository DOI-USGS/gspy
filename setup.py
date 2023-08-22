#!/usr/bin/env python

import sys
# Test Python's version
major, minor = sys.version_info[0:2]
if (major, minor) < (3, 5):
    sys.stderr.write('\nPython 3.5 or later is needed to use this package\n')
    sys.exit(1)
from setuptools import find_packages, setup
from distutils.command.sdist import sdist
cmdclass={'sdist': sdist}

__version__ = '1.0.0'

setup(name='gspy',
    packages=find_packages(),
    scripts=[],
    version=__version__,
    description='Data handling',
    long_description='gspy converts commonly used data formats into a netcdf file honoring our GS convention.',
    url = 'https://github.com/usgs.gov',
    download_url=f"https://github.com/usgs/gspy/releases/v{__version__}.tar.gz",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
    ],
    author='Leon Foks, Stephanie James, Burke Minsley',
    author_email='nfoks@contractor.usgs.gov',
    install_requires=[
        'numpy',
        'xarray',
        'scipy',
        'h5py',
        'netcdf4',
        'matplotlib',
        'sphinx',
        'fortranformat',
        'rioxarray',
        'pyproj',
        'aseg-gdf2'
    ],
)
