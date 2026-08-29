"""
Magnetic Raster Dataset
-----------------------

These magnetic data channels were pulled from the Wisconsin SkyTEM example in this repository to demonstrate the relatively simple case of gridded raster files. 

Source Reference: Minsley, B.J, Bloss, B.R., Hart, D.J., Fitzpatrick, W., Muldoon, M.A., Stewart, E.K., Hunt, R.J., James, S.R., Foks, N.L., and Komiskey, M.J., 2022, Airborne electromagnetic and magnetic survey data, northeast Wisconsin (ver. 1.1, June 2022): U.S. Geological Survey data release, https://doi.org/10.5066/P93SY9LI.
"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy
from gspy import Survey
import warnings
warnings.filterwarnings('ignore')

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = '..//data_files//magnetics'

# Survey metadata file
metadata = join(data_path, "WI_Magnetics_survey_md.yml")

# Establish the Survey
survey = Survey.from_dict(metadata)

#%%
#
# .. literalinclude:: /../../examples/data_files/magnetics/WI_Magnetics_survey_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Survey YAML file
#

#%%
# Create a Data Branch
# ^^^^^^^^^^^^^^^^^^^^
data_container = survey.gs.add_container('magnetic_data', **dict(content = "raw flightline and gridded magnetic data", comment = "grids were contractor-derived"))


#%%
# Add the raw magnetic data to the branch
# """""""""""""""""""""""""""""""""""""""

# Import raw magnetic data from CSV-format.
d_data1 = join(data_path, 'WI_Magnetics.csv')
d_supp1 = join(data_path, 'WI_Magnetics_raw_data_md.yml')

#%%
rd = data_container.gs.add(key='raw_data', data=d_data1, metadata_file=d_supp1)

#%%
#
# .. literalinclude:: /../../examples/data_files/magnetics/WI_Magnetics_raw_data_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Raw Magnetic Data YAML file
#

#%%
# Add the Gridded Data
# """"""""""""""""""""

#%%
# Import a tif of gridded mag data.
# The metadata file for raster datasets should contain paths to the raster files.

d_supp1 = join(data_path, 'WI_Magnetics_grids_md.yml')
gd = data_container.gs.add(key='grids', metadata_file=d_supp1)

#%%
#
# .. literalinclude:: /../../examples/data_files/magnetics/WI_Magnetics_grids_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Gridded (Raster) Magnetic YAML file
#


#%%
# Save to NetCDF file
# ^^^^^^^^^^^^^^^^^^^

d_out = join(data_path, 'magnetics.nc')
survey.gs.to_netcdf(d_out)

# %%
# Opening a GS NetCDF 
# ^^^^^^^^^^^^^^^^^^^

new_survey = gspy.open_datatree(d_out)['survey']

#%%
# View the Data Tree
# ^^^^^^^^^^^^^^^^^^

print(new_survey)

#%%
# Plotting
# ^^^^^^^^

plt.figure()
new_survey['magnetic_data/raw_data']['height'].plot()
plt.tight_layout()

#%%
pd = new_survey['magnetic_data/raw_data']['tmi']
plt.figure()
pd.plot()
plt.tight_layout()

#%%
m = new_survey['magnetic_data/grids/magnetic_tmi']
plt.figure()
m.plot(cmap='jet')
plt.tight_layout()

plt.show()



