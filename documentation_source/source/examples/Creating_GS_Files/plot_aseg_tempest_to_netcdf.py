"""
ASEG to NetCDF
--------------

This example demonstrates the workflow for creating a GS file from the `ASEG <https://www.aseg.org.au/sites/default/files/pdf/ASEG-GDF2-REV4.pdf>`_ file format, as well as how to add multiple associated datasets to the Survey (e.g., Tabular and Raster groups). Specifically, this AEM survey contains the following datasets:

1. Raw AEM data, from the Tempest system
2. Inverted resistivity models
3. An interpolated map of total magnetic intensity

Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""

#%%
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey

#%%
# Convert the ASEG data to NetCDF
# +++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//supplemental//region//MAP'

# Survey Metadata file
metadata = join(data_path, "data//Tempest_survey_md.json")

# Establish survey instance
survey = Survey(metadata)

#%%
# 1. Raw Data -
# Import raw AEM data from ASEG-format.
# Define input data file and associated metadata file
d_data = join(data_path, 'data//Tempest.dat')
d_supp = join(data_path, 'data//Tempest_data_md.json')

# Add the raw AEM data as a tabular dataset
survey.add_tabular(type='aseg', data_filename=d_data, metadata_file=d_supp)

#%%
# 2. Inverted Models -
# Import inverted AEM models from ASEG-format.
# Define input data file and associated metadata file
m_data = join(data_path, 'model//Tempest_model.dat')
m_supp = join(data_path, 'model//Tempest_model_md.json')

# Read model data and format as Tabular class object
survey.add_tabular(type='aseg', data_filename=m_data, metadata_file=m_supp)

#%%
# 3. Magnetic Intensity Map -
# Import the magnetic data from TIF-format.
# Define input metadata file (which contains the TIF filenames linked with desired variable names)
r_supp = join(data_path, 'data//Tempest_raster_md.json')

# Read data and format as Raster class object
survey.add_raster(metadata_file = r_supp)

# Save NetCDF file
d_out = join(data_path, 'data//Tempest.nc')
survey.write_netcdf(d_out)

#%%
# Read back in the NetCDF file
new_survey = Survey.open_netcdf(d_out)

# Once the survey is read in, we can access variables like a standard xarray dataset.
print(new_survey.raster.magnetic_tmi)

# %%
# Plotting

# Make a scatter plot of a specific tabular variable, using GSPy's plotter
plt.figure()
new_survey.tabular[0].gs_tabular.scatter('Tx_Height', cmap='jet')

# Make a 2-D map plot of a specific raster variable, using Xarrays's plotter
plt.figure()
new_survey.raster['magnetic_tmi'].plot(vmin=-1000, vmax=1000, cmap='jet')
plt.show()
