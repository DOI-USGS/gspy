####################################################
Welcome to GSpy: Geophysical Data Standard in Python
####################################################

This package provides functions and workflows for standardizing geophysical datasets based on the NetCDF file format.
The current implementation supports both time and frequency domain electromagnetic data,
raw and processed, 1-D inverted models along flight lines, and 2-D/3-D gridded layers.

Suggested Citations
~~~~~~~~~~~~~~~~~~~

If you use this software to generate gspy conformant data we suggest citing the software itself.

Foks, N.L., James, S. R., and Minsely, B. J. 2022. GSPy: Geophysical Data Standard in Python. U.S. Geological Survey software release. doi:10.5066/P9XNQVGQ

The manuscript accompanying this software release defining the standard itself you can also cite the following.

James, S. R., Foks, N.L., and Minsely, B. J. 2022. GSPy: A new toolbox and data standard for Geophysical Datasets. Frontiers in Earth Science. 10. doi:10.3389/feart.2022.907614

Documentation
~~~~~~~~~~~~~

`Documentation is here! <https://usgs.github.io/gspy/>`_

Goals
~~~~~

1. Standardize a geophysical data format based on the CF convention and NetCDF.
2. Restructure raw and processed data, or model, products into a consistent format for release.
3. Document metadata pertinent to geophysical dataset release.
4. Develop tools for processing data and preparing data for inversion.
5. Develop exploratory tools to interrogate data.

NetCDF Data Standard
~~~~~~~~~~~~~~~~~~~~
Datasets are read from a variety of original formats (CSV, ASEG-GDF, TIF) and reconfigured to follow a NetCDF based data standard, which includes detailed metadata:

1. All variables have detailed attributes (units, null values, data format).
2. Contains supporting information on the airborne survey, data collection, and modeling parameters.
3. Standardized coordinate reference system (CRS) variables for maximum portability to other GIS software (QGIS, ArcGIS, etc).
4. Inputs with different CRSs are reprojected to be consistent for a given survey.

Installation
~~~~~~~~~~~~
pip install gspy
