"""
Basic Class Structure
---------------------

The three primary classes (Survey, Tabular, and Raster) all contain data and metadata within `Xarray <https://docs.xarray.dev/en/stable/>`_ Datasets. This example demonstrates how to access the xarray object for each class, and methods for exploring the data and metadata.

This example uses ASEG-formatted raw AEM data from the Tempest system, and a 2-D GeoTiFF of magnetic data.

Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey
from pprint import pprint

#%%
# First Create the Survey & Data Objects

# Initialize the Survey
data_path = '..//..//supplemental//region//MAP'
metadata = join(data_path, "data//Tempest_survey_md.json")
survey = Survey(metadata)

# Add Tabular and Raster Datasets
t_data = join(data_path, 'data//Tempest.dat')
t_supp = join(data_path, 'data//Tempest_data_md.json')
survey.add_tabular(type='aseg', data_filename=t_data, metadata_file=t_supp)
r_supp = join(data_path, 'data//Tempest_raster_md.json')
survey.add_raster(metadata_file = r_supp)

#%% 
# Accessing the Xarray object
# +++++++++++++++++++++++++++

################################################################################
# Survey

# The Survey's metadata is accessed through the xarray property
print('Survey:\n')
print(survey.xarray)

################################################################################
# To look just at the attributes
print('Survey Attributes:\n')
pprint(survey.xarray.attrs)

################################################################################
# Or expand a specific variable
print('Survey Information:\n')
print(survey.xarray['survey_information'])

################################################################################
# Tabular & Raster

################################################################################
# Datasets are attached to the Survey as lists, however if only one Dataset of a given 
# type is present then the xarray object is returned simply by the name of the group

# Tabular
print('Tabular:\n')
print(survey.tabular)

# Raster
print('\nRaster:\n')
print(survey.raster)

################################################################################
# Multiple Groups

# If more than one Dataset is present under the group, then the list begins indexing
# For example, let's add a second Tabular Dataset
m_data = join(data_path, 'model//Tempest_model.dat')
m_supp = join(data_path, 'model//Tempest_model_md.json')
survey.add_tabular(type='aseg', data_filename=m_data, metadata_file=m_supp)

################################################################################
# Now the first dataset is accessed at index 0
print('First Tabular Group:\n')
print(survey.tabular[0])

################################################################################
# and the second is located at index 1
print('Second Tabular Group:\n')
print(survey.tabular[1])

#%% 
# Coordinates, Dimensions, and Attributes
# +++++++++++++++++++++++++++++++++++++++

################################################################################
# All data variables must have dimensions, coordinate, and attributes

#%%
# Dimensions
# ^^^^^^^^^^

################################################################################
# Tabular data are typicaly 1-D or 2-D variables with the primary dimension being ``index``, which
# corresponds to the rows of the input text file representing individual measurements.
print(survey.tabular[1]['index'])

################################################################################
# If a dimension is not discrete, meaning it represents ranges (such as depth layers), 
# then the bounds on each dimension value also need to be defined, and are linked 
# to the dimension through the "bounds" attribute.
print('example non-discrete dimension:\n')
print(survey.tabular[1]['gate_times'])
print('\n\ncorresponding bounds on non-discrete dimension:\n')
print(survey.tabular[1]['gate_times_bnds'])
#%%
# Coordinates
# ^^^^^^^^^^^

################################################################################
# Coordinates define the spatial and temporal positioning of the data (X Y Z T). 
# Additionally, all dimensions are by default classified as a coordinate. 
# This means a dataset can have both dimensional and non-dimensional coordinates.
# Dimensional coordinates are noted with a * (or bold text) in printed output of the xarray,
# such as ``index``, ``gate_times``, ``nv`` in this example:
print(survey.tabular[0].coords)

################################################################################
# Tabular Coordinates

################################################################################
# In Tabular data, coordinates are typically non-dimensional, since the primary dataset
# dimension is ``index``. By default, we define the spatial coordinates, ``x`` and ``y``,
# based on the longitude and latitude (or easting/northing) data variables. If relevant, 
# ``z`` and ``t`` coordinate variables can also be defined, representing the vertical and 
# temporal coordinates of the data points. 

################################################################################
# Note: All coordinates must match the coordinate reference system defined in the Survey.

################################################################################
# Raster Coordinates

################################################################################
# Raster data are gridded, typically representing maps or multi-dimensional models.
# Therefore, Raster data almost always have dimensional coordinates, i.e., the 
# data dimensions correspond directly to either spatial or temporal coordinates (``x``, ``y``, ``z``, ``t``).
print(survey.raster.coords)

################################################################################
# The Spatial Reference Coordinate

################################################################################
# the ``spatial_ref`` coordinate variable is a non-dimensional coordinate that
# contains information on the coordinate reference system. For more information, 
# see :ref:`Coordinate Reference Systems <coordinate reference systems>`.

#%%
# Attributes
# ^^^^^^^^^^

################################################################################
# Both datasets and data variables have attributes (metadata fields). Certain 
# attributes are required, see our documentation on :ref:`the GS standard <GS Convention Requirements>`.
# for more details.

################################################################################
# Dataset attributes

################################################################################
# Dataset attributes provide users a way to document and describe supplementary 
# information about a dataset group as a whole, such as model inversion parameters
# or other processing descriptions. At a minimum, a ``content`` attribute should
# contain a brief summary of the contents of the dataset.
pprint(survey.tabular[1].attrs)

################################################################################
# Variable attributes

################################################################################
# Each data variable must contain attributes detailing the metadata 
# of that individual variable. These follow the `Climate and Forecast (CF) metadata conventions <http://cfconventions.org/>`_.
pprint(survey.tabular[1]['conductivity'].attrs)