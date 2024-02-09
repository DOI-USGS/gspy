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
data_path = '..//..//supplemental//region//MAP'

# Define ..//supplemental information file
..//supplemental = join(data_path, "data//Tempest_survey_md.json")

# Read in TIF data file
survey = Survey(..//supplemental)

# Define input TIF-format data file and associated variable mapping file
d_grid_supp = join(data_path, 'data//Tempest_raster_md.json')

# Read data and format as Griddata class object
survey.add_raster(metadata_file = d_grid_supp)

# Write NetCDF
d_out = join(data_path, 'data//tif.nc')

survey.write_netcdf(d_out)

#%%
# Read in the netcdf files
new_survey = Survey.open_netcdf(d_out)

#%%
# Plotting
plt.figure()
new_survey.raster['magnetic_tmi'].plot(vmin=-1000, vmax=1000, cmap='jet')
plt.show()