"""
TIF to NetCDF conversion
-------------------------
Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey

#%%
# Convert the TIF data to netcdf
# ++++++++++++++++++++++++++++++

# Path to example files
data_path = '..//..//supplemental//'

# Define ..//supplemental information file
..//supplemental = data_path + "region//MAP//data//Tempest_survey_information.json"

# Read in TIF data file
survey = Survey(..//supplemental)

# Define input ASEG-format data file and associated variable mapping file
d_data = data_path + 'region//MAP//data//Tempest.dat'
d_supp = data_path + 'region//MAP//data//Tempest_data_information.json'

# Read data and format as Linedata class object
# survey.add_tabular(type='aseg', data_filename=d_data, metadata_file=d_supp)

# Define input TIF-format data file and associated variable mapping file
d_grid_path = data_path + 'region//MAP//data//'
d_grid_supp = data_path + 'region//MAP//data//Tempest_raster_Attributes.json'

# Read data and format as Griddata class object
survey.add_raster(metadata_file=d_grid_supp)

# Write NetCDF
d_out = data_path + 'region//MAP//data//tif.nc'

survey.write_netcdf(d_out)

#%%
# Read in the netcdf files
new_survey = Survey.open_netcdf(d_out)

#%%
# Plotting
plt.figure()
new_survey.raster.pcolor('magnetic_tmi', vmin=-1000, vmax=1000, cmap='jet')
plt.show()