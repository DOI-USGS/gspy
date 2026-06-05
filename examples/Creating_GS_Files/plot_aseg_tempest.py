"""
ASEG-GDF (Tempest AEM) & Magnetic Raster
----------------------------------------

This example demonstrates the workflow for creating a GS file from the `ASEG <https://www.aseg.org.au/sites/default/files/pdf/ASEG-GDF2-REV4.pdf>`_ file format, as well as how to add multiple associated datasets to the Survey. Specifically, this AEM survey contains the following datasets:

1. Raw AEM data, from the Tempest system
2. Inverted resistivity models
3. An interpolated map of total magnetic intensity

Dataset Reference: `Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.`

"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = "..//data_files//tempest_aseg"

# Survey Metadata file
metadata = join(data_path, "data//Tempest_survey_md.yml")

# Establish survey instance
survey = gspy.Survey.from_dict(metadata)

#%%
# Create the first branch (container) called "data"
data_container = survey.gs.add_container('data', **dict(content = "raw data"))

#%%
# Attach leaves to the data branch
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# 1. Raw Data

#%%
# Import raw AEM data from ASEG-GDF2 format.
# Define input data file and associated metadata file. Note for ASEG-GDF2 files, variable metadata is pulled directly from the DFN file associated with the DAT file. Any additional variable metadata, or desired overwrites to the DFN values, can be passed through the YAML. 

# In this example, multiple systems are defined in the Tempest_data_md.yml metadata file
d_data = join(data_path, 'data//Tempest.dat')
d_supp = join(data_path, 'data//Tempest_data_md.yml')

# Add the raw AEM data to the data branch
rd = data_container.gs.add(key='raw_data', 
                           data_filename=d_data, 
                           metadata_file=d_supp)

#%%
# 2. Inverted Models
model_container = survey.gs.add_container('models', **dict(content = "inverted 1-D electrical resistivity models"))

# Define Path to inverted AEM models and corresponding metadata file
m_data = join(data_path, 'model//Tempest_model.dat')
m_supp = join(data_path, 'model//Tempest_model_md.yml')

# Add models to the model container, note this example contains a "parameters" group that
# is added as a leaflet below the model group.
mod = model_container.gs.add(key='inverted_models', 
                             data_filename=m_data, 
                             metadata_file=m_supp, 
                             derived_from=rd)

#%%
# 3. Magnetic Intensity Map

# Create a new branch for the contractor-derived total magnetic intensity map
map_container = survey.gs.add_container('derived_maps', **dict(content = "derived maps"))

# Import the magnetic data from TIF-format.
# Note: raster data files are defined within the metadata file
d_supp = join(data_path, 'data//Tempest_raster_md.yml')

# Add the magnetic map to the data
maps = map_container.gs.add(key='maps', metadata_file = d_supp)

#%%
# View the Data Tree
# ^^^^^^^^^^^^^^^^^^
print(survey)

#%%
# Save NetCDF file
# ^^^^^^^^^^^^^^^^

d_out = join(data_path, 'Tempest.nc')
survey.gs.to_netcdf(d_out)

#%%
#Read back in the NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

#%%
# Once the survey is read in, we can access variables like a standard xarray dataset.

#%%
# Option A:
print(new_survey['derived_maps/maps'].magnetic_tmi)
#%%
# Option B:
print(new_survey['derived_maps/maps']['magnetic_tmi'])

# %%
# Plotting Examples
# ^^^^^^^^^^^^^^^^^
# demonstrating different ways to access and plot variables

# Make a scatter plot of a specific tabular variable, using GSPy's plotter
plt.figure()
new_survey['data']['raw_data'].gs.scatter(x='x', hue='tx_height', cmap='jet')

#%%
# Make a 2-D map plot of a specific raster variable, using Xarrays's plotter
plt.figure()
new_survey['derived_maps/maps']['magnetic_tmi'].plot(cmap='jet', robust=True)
plt.show()