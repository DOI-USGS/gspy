"""
Multi-dataset Survey
--------------------

This example demonstrates the typical workflow for creating a GS file for an AEM survey in its entirety, i.e., the NetCDF file contains all related datasets together, e.g., raw data, processed data, inverted models, and derivative products. Specifically, this survey contains:

1. Minimally processed (raw) AEM data and raw/processed magnetic data provided by SkyTEM
2. Fully processed AEM data used as input to inversion
3. Laterally constrained inverted resistivity models
4. Point-data estimates of bedrock depth derived from the AEM models
5. Interpolated magnetic and bedrock depth grids

Note:
To make the size of this example more managable, some of the input datasets have been downsampled relative to the source files in the data release referenced below.

Dataset Reference:
Minsley, B.J, Bloss, B.R., Hart, D.J., Fitzpatrick, W., Muldoon, M.A., Stewart, E.K., Hunt, R.J., James, S.R., Foks, N.L., and Komiskey, M.J., 2022, Airborne electromagnetic and magnetic survey data, northeast Wisconsin (ver. 1.1, June 2022): U.S. Geological Survey data release, https://doi.org/10.5066/P93SY9LI.
"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy
from gspy import Survey
import xarray as xr


#%%
# Convert the Skytem csv data to NetCDF
# +++++++++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//..//..//example_material//example_1'

# Survey metadata file
metadata = join(data_path, "data//WI_SkyTEM_survey_md.yml")

# Establish the Survey
survey = Survey.from_dict(metadata)

data_container = survey.gs.add_container('data', **dict(content = "raw and processed data",
                                                        comment = "This is a test"))

#%%
# 1 - Raw Data -
# Import raw AEM data from CSV-format.
# Define input data file and associated metadata file
d_data1 = join(data_path, 'data//WI_SkyTEM_2021_ContractorData.csv')
d_supp1 = join(data_path, 'data//WI_SkyTEM_raw_data_md.yml')

# Add the raw AEM data as a tabular dataset
data_container.gs.add(key='raw_data', data_filename=d_data1, metadata_file=d_supp1, system=survey.nominal_system)

print(data_container)

#%%
# 2 - Processed Data -
# Import processed AEM data from CSV-format.
# Define input data file and associated metadata file
d_data2 = join(data_path, 'data//WI_SkyTEM_2021_ProcessedData.csv')
d_supp2 = join(data_path, 'data//WI_SkyTEM_processed_data_md.yml')

system = {"skytem_system" : survey["nominal_system"].isel(lm_gate_times=np.s_[1:], hm_gate_times=np.s_[10:]),
          "magnetic_system" : survey["magnetic_system"]}

# Add the processed AEM data as a tabular dataset
pd = data_container.gs.add(key='processed_data', data_filename=d_data2, metadata_file=d_supp2, system=system)

#%%
# 3 - Inverted Models -

# Create a new container for models
model_container = survey.gs.add_container('models', **dict(content = "Inverted models",
                                                          comment = "This is a test"))

# Import inverted AEM models from CSV-format.
# Define input data file and associated metadata file
m_data3 = join(data_path, 'model//WI_SkyTEM_2021_InvertedModels.csv')
m_supp3 = join(data_path, 'model//WI_SkyTEM_inverted_models_md.yml')

# Add the inverted AEM models as a tabular dataset
model_container.gs.add(key='inverted_models', data_filename=m_data3, metadata_file=m_supp3)

#%%
# 4 - Bedrock Picks -
# Import AEM-based estimated of depth to bedrock from CSV-format.
# Define input data file and associated metadata file
d_data4 = join(data_path, 'data//topDolomite_Blocky_LidarDEM.csv')
d_supp4 = join(data_path, 'data//WI_SkyTEM_bedrock_picks_md.yml')

# Add the AEM-based estimated of depth to bedrock as a tabular dataset
data_container.gs.add(key='depth_to_bedrock', data_filename=d_data4, metadata_file=d_supp4)

#%%
# 5 - Derivative Maps -

# We can add arbitrarily named containers to the survey
derived_products = survey.gs.add_container('derived_products', **dict(content = "products derived from other data and models"))

# Import interpolated bedrock and magnetic maps from TIF-format.
# Define input metadata file (which contains the TIF filenames linked to variable names)
m_supp5 = join(data_path, 'data//WI_SkyTEM_mag_bedrock_grids_md.yml')

# Add the interpolated maps as a raster dataset
derived_products.gs.add(key='maps', metadata_file=m_supp5)

#%%
# Save to NetCDF file
d_out = join(data_path, 'model//WISkyTEM.nc')
survey.gs.to_netcdf(d_out)

#%%
# The gspy goal is to have the complete survey in a single file. However, we can also save containers or datasets separately.

data_container.gs.to_netcdf('test_datacontainer.nc')

#%%
# Reading back in
new_survey = gspy.open_datatree(d_out)['survey']

print(new_survey)

#%%
# Plotting
plt.figure()
new_survey['data']['raw_data']['height'].plot()
plt.tight_layout()

pd = new_survey['data']['processed_data']
plt.figure()
pd['elevation'].plot()
plt.tight_layout()

m = new_survey['derived_products']['maps']
plt.figure()
m['magnetic_tmi'].plot(cmap='jet')
plt.tight_layout()

plt.show()
