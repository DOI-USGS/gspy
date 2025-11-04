"""
Magnetic Survey
---------------

These magnetic data channels were pulled from the Wisconsin Skytem example in this repository

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
from pprint import pprint


#%%
# Convert the magnetic csv data to NetCDF
# +++++++++++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//..//..//example_material//mag_example'

# Survey metadata file
metadata = join(data_path, "WI_Magnetics_survey_md.yml")

# Establish the Survey
survey = Survey.from_dict(metadata)

data_container = survey.gs.add_container('data', **dict(content = "raw and gridded data",
                                                        comment = "This is a test"))

#%%
# 1 - Raw Data -
# Import raw mag data from CSV-format.
# Define input data file and associated metadata file
d_data1 = join(data_path, 'WI_Magnetics.csv')
d_supp1 = join(data_path, 'WI_Magnetics_raw_data_md.yml')

# Add the raw AEM data as a tabular dataset
data_container.gs.add(key='raw_data', data_filename=d_data1, metadata_file=d_supp1)

#%%
# 1 - Gridded Data -
# Import a tif of gridded mag data.
d_supp1 = join(data_path, 'WI_Magnetics_grids_md.yml')

# Add the raw AEM data as a tabular dataset
data_container.gs.add(key='grids', metadata_file=d_supp1)

#%%
# Save to NetCDF file
d_out = join(data_path, 'WI_Magnetics.nc')
survey.gs.to_netcdf(d_out)

#%%
# Reading back in
new_survey = gspy.open_datatree(d_out)['survey']

print(new_survey)

#%%
# Plotting
plt.figure()
new_survey['data/raw_data']['height'].plot()
plt.tight_layout()

pd = new_survey['data/raw_data']['tmi']
plt.figure()
pd.plot()
plt.tight_layout()

m = new_survey['data/grids/magnetic_tmi']
plt.figure()
m.plot(cmap='jet')
plt.tight_layout()

plt.show()



