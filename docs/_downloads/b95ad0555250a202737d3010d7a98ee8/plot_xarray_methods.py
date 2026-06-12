"""
Basic Functionality
-------------------

The GS standard organizes datasets and metadata within a Data Tree. In GSPy, this is implemented through accessors into `Xarray <https://docs.xarray.dev/en/stable/>`_ DataTrees, Datasets, and DataArrays. This example demonstrates basic xarray functionality for exploring the data and metadata for each class type.

This example uses the TEMPEST AEM survey as a basis for demonstration.

Source Reference: `Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.`

"""
#%%
import matplotlib.pyplot as plt
from os.path import join, isfile
import gspy
from gspy import Survey
from pprint import pprint

#%%
# First open the netcdf GS standard file, generate it if doesn't already exist
input_file = "..//data_files//tempest_aseg//Tempest.nc"
if not isfile(input_file):
    import subprocess
    import sys
    subprocess.run([sys.executable, "..//Creating_GS_Files//plot_aseg_tempest.py"])
survey = gspy.open_datatree(input_file)['survey']

#%%
# Accessing the groups within the tree
# ++++++++++++++++++++++++++++++++++++

#%%
# Survey

#%%
# the ``survey`` object here is a DataTree, printing it will show the entire contents
# of the DataTree
print('Survey:\n')
print(survey)

#%%
# The DataSet object at the location /survey can be isolated through two options:

#%%
# Option 1) directly form the DataTree object ``survey``
print('\n\nOption 1:\n')
print(survey.dataset)

#%%
# or Option 2) use the path to the group and then retrieve the DataSet
print('\n\nOption 2:\n')
print(survey['/survey'].dataset)

#%%
# To look just at the attributes of the Survey, once again it can be accessed
# either directly or by using the group path

#%%
# Survey Attributes Option 1:
pprint(survey.attrs)

#%%
# Survey Attributes Option 2:
pprint(survey['/survey'].attrs)

#%%
#  Similarly, to expand a specific variable of the survey, we can access it
# directly from the survey object, i.e. no path needed first
print('\n\nSurvey Information:\n')
print(survey['survey_information'])

#%%
# DataTree Items

#%%
# The method "items" on a DataTree returns the variables within the top-level
# Dataset (in this case /survey) and all children. Note this does not return
# grandchildren! So in this case we only see the container branches immediately
# beneath the survey

print('\n\nItems of the Survey DataTree\n')
for name, item in survey.items():
    # do something with the item if desired
    print(name)

#%%
# Datasets are attached to the DataTree and can be isolated by their path. If a
# Dataset has children beneath it then technically it is still a DataTree object
# and printing it will show the rest of that branch of the tree.

# Show the data branch
print('\n\nData Branch:\n')
print(survey['data'])

#%%
# Zoom in to the lowest level of the tree, notice it is still technically a DataTree
# object but it has no children.
print('\n\nSystem Leaflet at the bottom of the Tree:\n')
print(survey['data/raw_data/tempest_system'])

#%%
# Use the .to_dataset method to isolate the Dataset (convert from DataTree to
# Dataset), can optionally create a new variable with just that Dataset:
tempest_system = survey['data/raw_data/tempest_system'].to_dataset()
print('\n\nSystem Leaflet, as a Dataset:\n')
print(tempest_system)

#%%
# !!!! Important !!!! This returns an copy from the DataTree, i.e. any changes to
# tempest_system does not change the source. For example:
tempest_system.attrs['aaaaaaa'] = 'adding a new attribute'
print('\n\nAltered attributes on the DataSet:')
pprint(tempest_system.attrs)
print('\n\nSource group attributes do not see the new attribute:')
pprint(survey['data/raw_data/tempest_system'].attrs)

#%%
# Coordinates, Dimensions, and Attributes
# +++++++++++++++++++++++++++++++++++++++

#%%
# Dimensions
# ^^^^^^^^^^

#%%
# Dimensions are simply ``name: length`` pairs corresponding to the dimension
# coordinate variables represented in the specific Dataset group being examined

# use the method "sizes" to see a list of all the dimensions of a group
print('\n\nDimensions:\n')
print(survey['models/inverted_models'].sizes)

#%%
# Isolate an individual dimension coordinate for further examination

#%%
# Tabular data are typically 1-D or 2-D variables with the primary dimension
# being ``index``, which often corresponds to the rows of the input text
# file representing individual measurements.
print('\n\nLooking at the Index dimension coordinate:\n')
print(survey['models/inverted_models']['index'])

#%%
# If a dimension is not discrete, meaning it represents ranges (such as depth layers),
# then the bounds on each dimension value also need to be defined, and are linked
# to the dimension through the "bounds" attribute.
print('\n\nExample of a non-discrete dimension:\n')
print(survey['models/inverted_models']['layer_depth'])

#%%
# Notice that the bounds variable is 2-D [index, nv] where nv = number of vertices,
# in this case of length 2:
print('\n\nCorresponding bounds on this non-discrete dimension:\n')
print(survey['models/inverted_models']['layer_depth_bnds'])

#%%
print('\n\nSee the bounds:\n')
print(survey['models/inverted_models']['layer_depth_bnds'].values)

#%%
# Coordinates
# ^^^^^^^^^^^

#%%
# Coordinates define the spatial and temporal positioning of the data (X Y Z T).
# Additionally, all dimensions are linked to dimension coordinate variables that
# house the coordinates (i.e. values) of that dimension.
# This means a dataset can have both dimensional and non-dimensional coordinates.
# Dimensional coordinates are noted with a * (or bold text) in printed output of
# the xarray, such as ``index`` and ``gate_times`` in this example.
print('\n\nInspect the coordinates of a tabular dataset:\n')
print(survey['data/raw_data'].dataset.coords)

#%%
# Tabular Coordinates

#%%
# In Tabular data, coordinates are typically non-dimensional, since the primary
# dataset dimension is ``index``. By default, we define the spatial coordinates,
# ``x`` and ``y``, based on the longitude and latitude (or easting/northing)
# data variables. If relevant, ``z`` and ``t`` coordinate variables can also be
# defined, representing the vertical and temporal coordinates of the data points.
# Per CF conventions, these spatiotemporal coordinates have extra attributes
# required such as "axis" and strict requirements on "standard_names" to make
# the datasets recognizable to GIS software. GSPy handles automatically handles
# these requirements for users.
print('\n\nInspecting a specific coordinate variable:\n')
print(survey['data/raw_data']['x'])

#%%
# Note: All coordinates must match the coordinate reference system defined in
# the Survey.

#%%
# Raster Coordinates

#%%
# Raster data are gridded, typically representing maps or multi-dimensional
# models.Therefore, Raster data almost always have dimensional coordinates, i.e.,
# the data dimensions correspond directly to either spatial or temporal
# coordinates (``x``, ``y``, ``z``, ``t``).
print('\n\nInspect the coordinates of a raster dataset:\n')
print(survey['derived_maps/maps'].coords)

#%%
# The Spatial Reference Coordinate

#%%
# the ``spatial_ref`` coordinate variable is a non-dimensional coordinate that
# contains information on the coordinate reference system. All groups within the
# DataTree inherit the same spatial_ref. For more information, see :ref:`Coordinate Reference Systems <coordinate reference systems>`.
print('\n\nCRS spatial_ref variable:\n')
print(survey['derived_maps/maps']['spatial_ref'])

#%%
# Attributes
# ^^^^^^^^^^

###############################################################################
# Both datasets and data variables have attributes (metadata fields). Certain
# attributes are required, see our documentation on :ref:`Metadata Requirements <metadata-requirements>`
# for more details.

#%%
# Dataset attributes

#%%
# Dataset attributes provide users a way to document and describe supplementary
# information about a dataset group as a whole, such as model inversion parameters
# or other processing descriptions. At a minimum, a ``content`` attribute should
# contain a brief summary of the contents of the dataset.
print('\n\nDataset Attributes:\n')
pprint(survey['models/inverted_models'].attrs)

#%%
# Variable attributes

#%%
# Each data variable must contain attributes detailing the metadata
# of that individual variable. These follow the `Climate and Forecast (CF) metadata conventions <http://cfconventions.org/>`_.
print('\n\nDataArray (variable) Attributes:\n')
pprint(survey['models/inverted_models']['conductivity'].attrs)

#%%
# Filtering & Searching
# +++++++++++++++++++++

#%%
# The required keys can be used to search through a tree and 
# find groups of interest

#%%
# Here's a simply function using native netCDF and xarray methods to search
# through a file and identify groups based on their attributes

import xarray as xr
from netCDF4 import Dataset

def find_groups_by_attrs(nc_path, find_attr='type', find_value=None):
    with Dataset(nc_path, mode="r") as ds:
        def walk(group, path=""):
            for attr in group.ncattrs():
                if attr == find_attr:
                    if find_value:
                        cur_value = group.getncattr(attr)
                        if isinstance(cur_value, list):
                            for ind_value in cur_value:
                                if ind_value == find_value:
                                    print(f"Group: {path}")
                                    print(f"\t{attr} = {group.getncattr(attr)!r}")
                        else:
                            if cur_value == find_value:
                                print(f"Group: {path}")
                                print(f"\t{attr} = {group.getncattr(attr)!r}")
                    else:
                        print(f"Group: {path}")
                        print(f"\t{attr} = {group.getncattr(attr)!r}")
            # Recurse into subgroups
            for gname, subg in group.groups.items():
                walk(subg, path + "/" + gname)
        walk(ds)

#%%
# see all the groups and their types
find_groups_by_attrs(input_file, find_attr='type')

#%%
# find just the system type groups
find_groups_by_attrs(input_file, find_attr='type', find_value='system')

#%%
# find just the model type groups
find_groups_by_attrs(input_file, find_attr='type', find_value='model')

#%%
# find every group related to the 'magnetic' method
find_groups_by_attrs(input_file, find_attr='method', find_value='magnetic')

#%%
# Then if you want to open one of these groups now that you see the path, 
# without GSPy just native xarray. Notice this opens just that single group,
# you do not have access to the rest of the datatree here:

ds = xr.open_dataset(input_file, group='/survey/derived_maps/maps')

print(ds)

#%%
# If you want to open a datatree, point the group to where you want to start
# the tree, can be '/survey' for the entire tree, or in this case we load
# just the models branch:

dt = xr.open_datatree(input_file, group='/survey/models',
                      decode_timedelta=True)

print(dt)