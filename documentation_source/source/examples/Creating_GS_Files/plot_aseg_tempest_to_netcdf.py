"""
ASEG to NetCDF
--------------

This example demonstrates the workflow for creating a GS file from the `ASEG <https://www.aseg.org.au/sites/default/files/pdf/ASEG-GDF2-REV4.pdf>`_ file format, as well as how to add multiple associated datasets to the Survey (e.g., Tabular and Raster groups). Specifically, this AEM survey contains the following datasets:

1. Raw AEM data, from the Tempest system
2. Inverted resistivity models
3. An interpolated map of total magnetic intensity

Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy

#%%
# Convert the ASEG data to NetCDF
# +++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//..//..//example_material//example_2'

# Survey Metadata file
metadata = join(data_path, "data//Tempest_survey_md.yml")

# Establish survey instance
survey = gspy.Survey.from_dict(metadata)

#%%
# 1. Raw Data -
data_container = survey.gs.add_container('data', **dict(content = "raw and processed data"))

# Import raw AEM data from ASEG-format.
# Define input data file and associated metadata file
d_data = join(data_path, 'data//Tempest.dat')
d_supp = join(data_path, 'data//Tempest_data_md.yml')

# Add the raw AEM data as a tabular dataset
rd = data_container.gs.add(key='raw_data', data_filename=d_data, metadata_file=d_supp)

#%%
# 2. Inverted Models
model_container = survey.gs.add_container('models', **dict(content = "inverted models"))

# Import inverted AEM models from ASEG-format.
# Define input data file and associated metadata file
m_data = join(data_path, 'model//Tempest_model.dat')
m_supp = join(data_path, 'model//Tempest_model_md.yml')

# Read model data and format as Tabular class object
model_container.gs.add(key='inverted_models', data_filename=m_data, metadata_file=m_supp)

#%%
# 3. Magnetic Intensity Map
data_derived = data_container.gs.add_container('derived_maps', **dict(content = "derived maps"))

# Import the magnetic data from TIF-format.
# Define input metadata file (which contains the TIF filenames linked with desired variable names)
r_supp = join(data_path, 'data//Tempest_raster_md.yml')

# Read data and format as Raster class object
data_derived.gs.add(key='maps', metadata_file = r_supp)

# Save NetCDF file
d_out = join(data_path, 'data//Tempest.nc')
survey.gs.to_netcdf(d_out)

#%%
# Read back in the NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

# Once the survey is read in, we can access variables like a standard xarray dataset.
print(new_survey['data/derived_maps/maps'].magnetic_tmi)
print(new_survey['data/derived_maps/maps']['magnetic_tmi'])

# %%
# Plotting

# Make a scatter plot of a specific tabular variable, using GSPy's plotter
plt.figure()
new_survey['data']['raw_data'].gs.scatter(x='x', hue='tx_height', cmap='jet')

# Make a 2-D map plot of a specific raster variable, using Xarrays's plotter
plt.figure()
new_survey['data/derived_maps/maps']['magnetic_tmi'].plot(cmap='jet', robust=True)
plt.show()
