"""
ASEG to NetCDF conversion
-------------------------
Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""

#%%
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey

#%%
# Convert the ASEG data to netcdf
# +++++++++++++++++++++++++++++++

# Path to example files
data_path = '..//..//supplemental//'

# Survey Metadata file
..//supplemental = data_path + "region//MAP//data//Tempest_survey_information.json"

# Establish survey instance
survey = Survey(..//supplemental)

# Define input ASEG-format data file and associated variable mapping file
d_data = data_path + 'region//MAP//data//Tempest.dat'
d_supp = data_path + 'region//MAP//data//Tempest_data_information.json'

# Read data and format as Tabular class object
survey.add_tabular(type='aseg', data_filename=d_data, metadata_file=d_supp)

# Define input ASEG-format model file and associated variable mapping file
m_data = data_path + 'region//MAP//model//Tempest_model_0.dat'
m_supp = data_path + 'region//MAP//model//Tempest_model_information.json'

# Read model data and format as Tabular class object
survey.add_tabular(type='aseg', data_filename=m_data, metadata_file=m_supp)

# Save NetCDF file
d_out = data_path + 'region//MAP//data//Tempest.nc'
survey.write_netcdf(d_out)

#%%
# Read in the netcdf files
new_survey = Survey.open_netcdf(d_out)

#%%
# Plotting
plt.figure()
new_survey.tabular[0].scatter('X_PrimaryField')

plt.figure()
new_survey.tabular[1].scatter('PhiD')

plt.show()