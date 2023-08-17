"""
Basic Class Structure and Xarray Methods
----------------------------------------

The three primary classes (Survey, Tabular, and Raster) all contain data and metadata within `Xarray <https://docs.xarray.dev/en/stable/>`_ Datasets. This example demonstrates how to access the xarray object for each class, and methods for exploring the data and metadata.

This example uses ASEG-formatted raw AEM data from the Tempest system, and a 2-D GeoTiFF of magnetic data.

Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey

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

# Survey
# The Survey's metadata is accessed through the xarray property
print(survey.xarray)

# To look just at the attributes
print(survey.xarray.attrs)

# Or expand a specific variable
print(survey.xarray['survey_information'])

# Tabular & Raster
# Datasets are attached to the Survey as lists, however if only one Dataset of a given 
# type is present then the xarray object is returned simply by the name of the group

# tabular
print(survey.tabular)

# raster
print(survey.raster)

# If more than one Dataset is present under the group, then the list begins indexing
# For example, let's add a second Tabular Dataset
m_data = join(data_path, 'model//Tempest_model.dat')
m_supp = join(data_path, 'model//Tempest_model_md.json')
survey.add_tabular(type='aseg', data_filename=m_data, metadata_file=m_supp)

# Now the first dataset is accessed at index 0
print(survey.tabular[0])

# and the second is located at index 1
print(survey.tabular[1])

#%% 
# Coordinates, Dimensions, and Attributes
# +++++++++++++++++++++++++++++++++++++++
