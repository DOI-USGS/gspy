"""
DAT & XYZ (Loupe TEM)
---------------------
This example demonstrates conversion of data from Loupe Geophysics' time domain electromagnetic (TEM) backpack system.

The raw data is in .dat format as exported by the Loupe. The inverted resistivity models come as a set of syn/dat/inv .XYZ files exported by Aarhus Workbench.

Source Reference: Minsley et al., in preparation, LoupeEM data and resistivity models from the Kankakee River groundwater-surface water interaction site, U.S. Geological Survey data release.
"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy
import warnings
warnings.filterwarnings('ignore')

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = '../data_files/loupe'

# Survey metadata file
metadata = join(data_path, "data//LoupeEM_survey_md.yml")

#%%
# Establish the Survey
survey = gspy.Survey.from_dict(metadata)

#%%
#
# .. literalinclude:: /../../examples/data_files/loupe/data/LoupeEM_survey_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Survey YAML file
#

#%%
# Create a 'data' branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

data_container = survey.gs.add_container('data', **dict(content='data container'))

#%%
# Attach raw data with the Loupe EM system

data = join(data_path, 'data//Kankakee.dat')
metadata = join(data_path, 'data//Loupe_data_metadata.yml')

#%%
raw_data = data_container.gs.add(key='raw_data', data_filename=data, 
                                 metadata_file=metadata, file_type='loupe')

#%%
#
# .. literalinclude:: /../../examples/data_files/loupe/data/Loupe_data_metadata.yml
#    :language: yaml
#    :linenos:
#    :caption: Raw Data YAML file
#

#%%
# Create a 'models' branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Make the branch
model_container = survey.gs.add_container('models', **dict(content='models container'))

#%%
# Import Workbench XYZ inversion results (syn/dat/inv)

#%%
# GSPy automatically recognizes Workbench inversion files (syn/dat/inv), only
# one of the three files need to be passed to provide the base filename

d_data = join(data_path, 'model//Kankakee_MOD_dat.xyz')
d_supp = join(data_path, 'model//models.yml')

#%%
md = model_container.gs.add(key='inversion', data_filename=d_data, metadata_file=d_supp)

#%%
#
# .. literalinclude:: /../../examples/data_files/loupe/model/models.yml
#    :language: yaml
#    :linenos:
#    :caption: Inverted Models YAML file
#

# %%
# Save to NetCDF file
# ^^^^^^^^^^^^^^^^^^^

d_out = join(data_path, 'Loupe.nc')
survey.gs.to_netcdf(d_out)

#%%
# Reading back in the GS NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

#%%
# Inspect the data tree
# ^^^^^^^^^^^^^^^^^^^^^
print(new_survey)

# %%
# Plotting
# ^^^^^^^^

plt.figure()
new_survey['data/raw_data']['gps_height'].plot(label='gps_height')
new_survey['data/raw_data']['tx_height'].plot(label='tx_height')
new_survey['data/raw_data']['rx_height'].plot(label='rx_height')
plt.tight_layout()
plt.legend()

plt.show()