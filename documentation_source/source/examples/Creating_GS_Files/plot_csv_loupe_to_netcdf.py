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


#%%
# Convert the Skytem csv data to NetCDF
# +++++++++++++++++++++++++++++++++++++

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
data_container.gs.add(key='raw_data', data_filename=data, metadata_file=metadata)

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