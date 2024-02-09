"""
CSV to NetCDF conversion
-------------------------
Dataset Reference:
Burton, B.L., Minsley, B.J., Bloss, B.R., and Kress, W.H., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2018 - February 2019: U.S. Geological Survey data release, https://doi.org/10.5066/P9XBBBUU.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey

#%%
# Convert the CSV data folder to netcdf
# ++++++++++++++++++++++++++++++++++++++

# Path to example files
data_path = '..//..//supplemental//'

metadata = data_path + "region//MAP//data//Resolve_survey_information.json"

# Establish the Survey
survey = Survey(metadata)

# Define input CSV-format data file and associated variable mapping file
d_data = data_path + 'region//MAP//data//Resolve.csv'
d_supp = data_path + 'region//MAP//data//Resolve_data_information.json'

# Read data and format as Linedata class object
survey.add_tabular(type='csv', data_filename=d_data, metadata_file=d_supp)

# Define input CSV-format model file and associated variable mapping file
m_data = data_path + 'region//MAP//model//Resolve_model_0.csv'
m_supp = data_path + 'region//MAP//model//Resolve_model_information.json'

# Read model data and format as Linemodel class object
survey.add_tabular(type='csv', data_filename=m_data, metadata_file=m_supp)

# Save NetCDF file
d_out = data_path + 'region//MAP//model//Resolve.nc'
survey.write_netcdf(d_out)

#%%
# Read in the netcdf files
new_survey = Survey.open_netcdf(d_out)

#%%
# Plotting
plt.figure()
new_survey.tabular[0].scatter('DTM', vmin=30, vmax=50)
plt.xlim([500000, 540000])
plt.ylim([1175000, 1210000])

plt.figure()
new_survey.tabular[1].scatter('DEM')
plt.show()