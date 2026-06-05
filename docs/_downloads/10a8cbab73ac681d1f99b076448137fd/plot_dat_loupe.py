"""
Loupe TEM
---------
This example demonstrates conversion of data from Loupe Geophysics' time domain electromagnetic (TEM) backpack system.

Dataset Reference:
Minsley et al., in preparation, LoupeEM data and resistivity models from the Kankakee River groundwater-surface water interaction site, U.S. Geological Survey data release.
"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy

#%%
# Convert the Loupe data and metadata from .dat and .desc files to NetCDF
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '../data_files/loupe'

# Survey metadata file
metadata = join(data_path, "data//LoupeEM_survey_md.yml")

# Establish the Survey
survey = gspy.Survey.from_dict(metadata)

# Make a data branch
data_container = survey.gs.add_container('data')

# Attach raw data with the Loupe EM system
# descriptive variable names ("long name") are read from DESC file when available, otherwise
# variable metadata comes from the YAML
data = join(data_path, 'data//Kankakee.dat')
metadata = join(data_path, 'data//Loupe_data_metadata.yml')
raw_data = data_container.gs.add(key='raw_data', data_filename=data, metadata_file=metadata, file_type='loupe')

# %%
# Save to NetCDF file
d_out = join(data_path, 'Loupe.nc')
survey.gs.to_netcdf(d_out)

#%%
# Reading back in
new_survey = gspy.open_datatree(d_out)['survey']

# Inspect the data tree
print(new_survey)
#%%
# Plotting
plt.figure()
new_survey['data/raw_data']['gps_height'].plot(label='gps_height')
new_survey['data/raw_data']['tx_height'].plot(label='tx_height')
new_survey['data/raw_data']['rx_height'].plot(label='rx_height')
plt.tight_layout()
plt.legend()

plt.show()