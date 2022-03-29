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

# def readme():
#     with open('README.rst', encoding='utf-8', mode='r') as f:
#         return f.read()

setup(name='gspy',
    packages=find_packages(),
    scripts=[],
    version="0.0.0",
    description='Data handling',
    long_description='', # readme(),
    url = '',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
    ],
    author='Leon Foks',
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
    # entry_points = {
    #     'console_scripts':[
    #         'geobipy=geobipy:geobipy',
    #         'geobipy_mpi=geobipy:geobipy_mpi',
    #     ],
    # }
)

