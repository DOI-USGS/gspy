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
from gspy import Survey

#%%
# Convert the Skytem csv data to NetCDF
# +++++++++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//supplemental//region//WI'

# Survey metadata file
metadata = join(data_path, "data//WI_SkyTEM_survey_md.json")

# Establish the Survey
survey = Survey(metadata)

#%%
# 1 - Raw Data -
# Import raw AEM data from CSV-format.
# Define input data file and associated metadata file
d_data1 = join(data_path, 'data//WI_SkyTEM_2021_ContractorData.csv')
d_supp1 = join(data_path, 'data//WI_SkyTEM_raw_data_md.json')

# Add the raw AEM data as a tabular dataset
survey.add_tabular(type='csv', data_filename=d_data1, metadata_file=d_supp1)

#%%
# 2 - Processed Data -
# Import processed AEM data from CSV-format.
# Define input data file and associated metadata file
d_data2 = join(data_path, 'data//WI_SkyTEM_2021_ProcessedData.csv')
d_supp2 = join(data_path, 'data//WI_SkyTEM_processed_data_md.json')

# Add the processed AEM data as a tabular dataset
survey.add_tabular(type='csv', data_filename=d_data2, metadata_file=d_supp2)

#%%
# 3 - Inverted Models -
# Import inverted AEM models from CSV-format.
# Define input data file and associated metadata file
m_data3 = join(data_path, 'model//WI_SkyTEM_2021_InvertedModels.csv')
m_supp3 = join(data_path, 'model//WI_SkyTEM_inverted_models_md.json')

# Add the inverted AEM models as a tabular dataset
survey.add_tabular(type='csv', data_filename=m_data3, metadata_file=m_supp3)

#%%
# 4 - Bedrock Picks -
# Import AEM-based estimated of depth to bedrock from CSV-format.
# Define input data file and associated metadata file
d_data4 = join(data_path, 'data//topDolomite_Blocky_LidarDEM.csv')
d_supp4 = join(data_path, 'data//WI_SkyTEM_bedrock_picks_md.json')

# Add the AEM-based estimated of depth to bedrock as a tabular dataset
survey.add_tabular(type='csv', data_filename=d_data4, metadata_file=d_supp4)

#%%
# 5 - Derivative Maps -
# Import interpolated bedrock and magnetic maps from TIF-format.
# Define input metadata file (which contains the TIF filenames linked to variable names)
m_supp5 = join(data_path, 'data//WI_SkyTEM_mag_bedrock_grids_md.json')

# Add the interpolated maps as a raster dataset
survey.add_raster(metadata_file=m_supp5)

#%%
# Save to NetCDF file
d_out = join(data_path, 'model//WISkyTEM.nc')
survey.write_netcdf(d_out)

# print a summary of the survey contents
print(survey.contents)

#%%
# Reading back in
new_survey = Survey().read_netcdf(d_out)

print(new_survey.spatial_ref.attrs)

print(new_survey.tabular[0]['LM_gate_times'])
print(new_survey.tabular[0]['LM_gate_times'].values[0])

#%%
# Plotting

# Make a figure of one of the raster data variables, using Xarray's plotter
plt.figure()
new_survey.raster['magnetic_tmi'].plot(cmap='jet')
plt.tight_layout()
plt.show()