####################################################
Welcome to GSpy: Geophysical Data Standard in Python
####################################################

This package provides functions and workflows for standardizing geophysical datasets based on the NetCDF file format.
The current implementation supports both time and frequency domain electromagnetic data,
raw and processed, 1-D inverted models along flight lines, and 2-D/3-D gridded layers.

Suggested Citations
~~~~~~~~~~~~~~~~~~~

If you use this software to generate gspy conformant data we suggest citing the software itself.

Foks, N.L., James, S. R., and Minsley, B. J. 2022. GSPy: Geophysical Data Standard in Python. U.S. Geological Survey software release. doi:10.5066/P9XNQVGQ

The manuscript accompanying this software release defining the standard itself you can also cite the following.

James, S. R., Foks, N.L., and Minsely, B. J. 2022. GSPy: A new toolbox and data standard for Geophysical Datasets. Frontiers in Earth Science. 10. doi:10.3389/feart.2022.907614

Documentation
~~~~~~~~~~~~~

`Documentation is here! <https://usgs.github.io/gspy/>`_

Goals
~~~~~

1. Standardize geophysical data into the Geophysical Survey (GS) data standard, based on the netCDF file format and CF metadata conventions.
2. Restructure various types of geophysical data (e.g., raw and processed data, inverted models, or derivative products) into a consistent format for sharing and archiving.
3. Document critical metadata pertinent to geophysical analysis and transferability.
4. Develop tools for generating and exploring standardized datasets, and facilitate handling of complex and diverse data and metadata information to accurately process, invert, and interpret geophysical data.
5. Develop visualization and exploratory tools to interrogate data.

Why netCDF?
~~~~~~~~~~~

   * **Metadata documentation** - detailed metadata is directly attached to the digital data values as variable-specific attributes (e.g., names, units, null values, value ranges) and as dataset attributes.
   * **Hierarchical structure** - multiple datasets can be organized into a single file within a tiered group structure. The GS standard takes advantage of this to define standardized group types and ordering to create an adaptable framework for organizing complex datasets with critical supporting information such as survey and acquisition details, system configurations, and modeling parameters.
   * **Portable and accessible format** - netCDF is platform-independent and supports subsetting which keeps large datasets accessible and easy to use.
   * **Well-established metadata conventions** - the CF convention provides a strong foundation for standardizing metadata and is widely recognized for netCDF files. For example, by following the CF guidelines for coordinate reference system (CRS) variables all GS files are accurately represented in GIS software (QGIS, ArcGIS, etc).
   * **Space-saving and scalable** - netCDF is a binary format with extra packing and compression options to significantly reduce file sizes, and is immediately scalable for large datasets with efficient read/write and parallel capabilities.

GSPy Workflow
~~~~~~~~~~~~~

The GSPy package provides tools for reading datasets from a variety of original formats common for geophysical data (e.g., CSV, ASEG-GDF, GeoTIFF), combining with metadata information, and generating standardized GS netCDF files.  

See our examples for detailed demonstrations of the GSPy workflow. In general, the steps for making a GS netCDF file are:

   1. Initiate a Survey

      * pass a metadata file (YAML or JSON) with global information about the survey

   2. Add a Container branch
   3. Add data to the Container branch

      * pass a data file 
      * pass a metadata file

   4. (optional) Add Supplementary Stem 

      * this can also be done simultaneous with Step 3 through the data's metadata file

   5. Repeat steps 2-4 for each dataset as needed
   6. Export to File

Installation
~~~~~~~~~~~~
pip install gspy
