"""
Loupe to NetCDF
---------------

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy

#%%
# Convert the Loupe csv data to NetCDF
# ++++++++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//..//..//example_material//example_3'

# Survey metadata file
metadata = join(data_path, "data//LoupeEM_survey_md.yml")

# Establish the Survey
survey = gspy.Survey.from_dict(metadata)

data_container = survey.gs.add_container('data')

data = join(data_path, 'data//Kankakee.dat')
metadata = join(data_path, 'data//Loupe_data_metadata.yml')
data_container.gs.add(key='raw_data', data_filename=data, metadata_file=metadata, file_type='loupe')

#%%
# Save to NetCDF file
d_out = join(data_path, 'data//Loupe.nc')
survey.gs.to_netcdf(d_out)

#%%
# Reading back in
new_survey = gspy.open_datatree(d_out)['survey']

#%%
# Plotting
plt.figure()
new_survey['data/raw_data']['height'].plot(label='height')
new_survey['data/raw_data']['tx_height'].plot(label='tx_height')
new_survey['data/raw_data']['rx_height'].plot(label='rx_height')
plt.tight_layout()
plt.legend()

plt.show()