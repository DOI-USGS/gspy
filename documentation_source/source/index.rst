####################################################
Welcome to GSpy: Geophysical Data Standard in Python
####################################################

.. image:: GSpy_logo.png
   :width: 600px
   :height: 516px
   :scale: 50 %
   :align: center


This package provides functions and workflows for standardizing geophysical datasets based on the NetCDF file format. The current implementation supports both tabular (unstructured or scattered) and raster (structured or gridded) datasets.

Goals
~~~~~

   1. Standardize a geophysical data format based on the `Climate and Forecast (CF) metadata conventions <http://cfconventions.org/>`_ and `NetCDF <https://www.unidata.ucar.edu/software/netcdf/>`_ format.
   2. Restructure various types of geophysical data (e.g., raw and processed data, inverted models, or derivative products) into a consistent format for sharing and archiving.
   3. Document critical metadata pertinent to geophysical analysis and transferability.
   4. Develop tools for processing data and preparing data for inversion.
   5. Develop exploratory and visualization tools to interrogate data.

NetCDF Data Standard
~~~~~~~~~~~~~~~~~~~~
Datasets are read from a variety of original formats (CSV, `ASEG-GDF <https://www.aseg.org.au/sites/default/files/pdf/ASEG-GDF2-REV4.pdf>`_, GeoTIFF) and reconfigured to follow a NetCDF based data standard, which includes detailed metadata:

   1. All variables have detailed attributes (names, units, null values, value ranges).
   2. Contains supporting information on the survey, data collection, and modeling parameters.
   3. Standardized coordinate reference system (CRS) variables for maximum portability to other GIS software (QGIS, ArcGIS, etc).
   4. Inputs with different CRSs are reprojected to be consistent for a given survey.
   5. NetCDF is immediately scalable for large datasets, it has efficient read/write and parallel capabilities.

.. toctree::
   :maxdepth: 12

   content/getting_started/getting_started
   content/api/api
   examples/index
   gspy_convention_requirements
