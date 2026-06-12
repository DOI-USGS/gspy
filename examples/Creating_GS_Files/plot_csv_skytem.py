"""
CSV & Rasters: Multi-dataset Survey with Derivative Products
------------------------------------------------------------

This example demonstrates the typical workflow for creating a GS file for an AEM survey in its entirety, i.e., the NetCDF file contains all related datasets together, e.g., raw data, processed data, inverted models, and derivative products. Specifically, this survey contains:

1. Minimally processed (raw) AEM data and raw/processed magnetic data provided by SkyTEM
2. Fully processed AEM data used as input to inversion
3. Laterally constrained inverted resistivity models
4. Point-data estimates of bedrock depth derived from the AEM models
5. Interpolated magnetic and bedrock depth grids

Note:
To make the size of this example more managable, some of the input datasets have been downsampled relative to the source files in the data release referenced below.

Source Reference: Minsley, B.J, Bloss, B.R., Hart, D.J., Fitzpatrick, W., Muldoon, M.A., Stewart, E.K., Hunt, R.J., James, S.R., Foks, N.L., and Komiskey, M.J., 2022, Airborne electromagnetic and magnetic survey data, northeast Wisconsin (ver. 1.1, June 2022): U.S. Geological Survey data release, https://doi.org/10.5066/P93SY9LI.
"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy
from gspy import Survey
import xarray as xr
from pprint import pprint
import warnings
warnings.filterwarnings('ignore')

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = '..//data_files//skytem_csv'

# Survey metadata file
metadata = join(data_path, "data//skytem_survey.yml")

# Establish the Survey
survey = Survey.from_dict(metadata)

#%%
#
# .. literalinclude:: /../../examples/data_files/skytem_csv/data/skytem_survey.yml
#    :language: yaml
#    :linenos:
#    :caption: Survey YAML file
#

#%%
# Create a Data Branch
# ^^^^^^^^^^^^^^^^^^^^

data_container = survey.gs.add_container('data', **dict(content = "raw and processed data",
                                                        comment = "<extra info goes here>"))

#%%
# Attach leaves to the data branch

#%%
# 1. Raw Data

# Import raw AEM data from CSV-format.
# Define input data file and associated metadata file
d_data1 = join(data_path, 'data//skytem_contractor_data.csv')
d_supp1 = join(data_path, 'data//skytem_contractor_data.yml')

raw_systems = {"skytem_system" : survey["nominal_system"],
          "magnetic_system" : survey["magnetic_system"]}

# Add the raw AEM data as a tabular dataset,
# pass the EM system from the survey
rd = data_container.gs.add(key='raw_data', data_filename=d_data1, 
                           metadata_file=d_supp1, system=raw_systems)

#%%
# 2. Processed Data

# Import processed AEM data from CSV-format.
# Define input data file and associated metadata file
d_data2 = join(data_path, 'data//skytem_processed_data.csv')
d_supp2 = join(data_path, 'data//skytem_processed_data.yml')

#%%
# Example of how systems can be selected and modified to accurately match the processed data
proc_systems = {"skytem_system" : survey["nominal_system"].isel(lm_gate_times=np.s_[1:], 
                                                          hm_gate_times=np.s_[10:]),
          "magnetic_system" : survey["magnetic_system"]}

#%%
# Add the processed AEM data as a tabular dataset, passing the updated systems
pd = data_container.gs.add(key='processed_data', data_filename=d_data2, 
                           metadata_file=d_supp2, system=proc_systems)

#%%
#
# .. literalinclude:: /../../examples/data_files/skytem_csv/data/skytem_processed_data.yml
#    :language: yaml
#    :linenos:
#    :caption: Processed Data YAML file
#

#%%
# Create a Models Branch
# ^^^^^^^^^^^^^^^^^^^^^^

# Create a new container for models
model_container = survey.gs.add_container('models', **dict(content = "Inverted models",
                                                          comment = "This is a test"))
#%%
# 3. Inverted Models

# Import inverted AEM models from CSV-format.
# Define input data file and associated metadata file
m_data3 = join(data_path, 'model//skytem_inverted_models.csv')
m_supp3 = join(data_path, 'model//skytem_inverted_models.yml')

# Add the inverted AEM models as a tabular dataset
mods = model_container.gs.add(key='inverted_models', data_filename=m_data3, 
                              metadata_file=m_supp3)

#%%
#
# .. literalinclude:: /../../examples/data_files/skytem_csv/model/skytem_inverted_models.yml
#    :language: yaml
#    :linenos:
#    :caption: Inverted Models YAML file
#

#%%
# Derivative Products
# ^^^^^^^^^^^^^^^^^^^

#%%
# 4. Bedrock Picks

#%%
# Adding bedrock picks to the 'data' branch

# Import AEM-based estimated of depth to bedrock from CSV-format.
# Define input data file and associated metadata file
d_data4 = join(data_path, 'data//top_dolomite_blocky_lidar.csv')
d_supp4 = join(data_path, 'data//bedrock_picks.yml')

# Add the AEM-based estimated of depth to bedrock as a tabular dataset
bedrock = data_container.gs.add(key='depth_to_bedrock', data_filename=d_data4, 
                                metadata_file=d_supp4)

#%%
#
# .. literalinclude:: /../../examples/data_files/skytem_csv/data/bedrock_picks.yml
#    :language: yaml
#    :linenos:
#    :caption: Bedrock Picks YAML file
#

#%%
# 5. Raster Maps

#%%
# Create a 3rd container for the derived raaster maps

derived_maps = survey.gs.add_container('derived_maps', **dict(content = "raster products derived from airborne data and models"))

# Import interpolated bedrock and magnetic maps from TIF-format.
# Define input metadata file (which contains the TIF filenames linked to variable names)
m_supp5 = join(data_path, 'data//magnetics_bedrock_picks.yml')

# Add the interpolated maps as a raster dataset
maps = derived_maps.gs.add(key='maps', metadata_file=m_supp5)

#%%
#
# .. literalinclude:: /../../examples/data_files/skytem_csv/data/magnetics_bedrock_picks.yml
#    :language: yaml
#    :linenos:
#    :caption: Gridded Maps YAML file
#

#%%
# Save to NetCDF file
# ^^^^^^^^^^^^^^^^^^^

d_out = join(data_path, 'skytem.nc')
survey.gs.to_netcdf(d_out)


#%%
# Export just one branch to file
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# The gspy goal is to have the complete survey in a single file. However, we can also save containers or datasets separately.

data_container.gs.to_netcdf(join(data_path, 'test_datacontainer.nc'))

# %%
# Opening a GS NetCDF 
# ^^^^^^^^^^^^^^^^^^^
new_survey = gspy.open_datatree(d_out)['survey']

#%%
# View the Data Tree
# ^^^^^^^^^^^^^^^^^^

print(new_survey.gs.tree)

#%%
print(new_survey)

# %%
# Plotting Examples
# ^^^^^^^^^^^^^^^^^

plt.figure()
new_survey['data']['raw_data']['height'].plot()
plt.tight_layout()

# %%
pcd = new_survey['data']['processed_data']
plt.figure()
pcd['tx_altitude'].plot()
plt.tight_layout()

# %%
m = new_survey['derived_maps']['maps']
plt.figure()
m['magnetic_tmi'].plot(cmap='jet')
plt.tight_layout()

plt.show()
