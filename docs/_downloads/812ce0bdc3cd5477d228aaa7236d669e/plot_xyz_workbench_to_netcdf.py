"""
Workbench XYZ
-------------

This example supports data and models read from Aarhus Workbench XYZ files. What's unique about these files is that metadata is embedded in the header of the data files, such as the electromagnetic gate times. 

The workbench file handler detects when an XYZ file matches this format and parses out the metadata to be joined with additional metadata passed from a YAML file. 

Source Reference: U.S. Geological Survey, 2024, Airborne electromagnetic and magnetic survey of Delaware Bay and surrounding regions of New Jersey and Delaware, 2022 (ver 2.0, April 2025): U.S. Geological Survey data release, https://doi.org/10.5066/F7J96592.
"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^
#
# .. literalinclude:: /../../examples/data_files/workbench/survey.yml
#    :language: yaml
#    :linenos:
#    :caption: this is a test
#

#%%
# Path to example files
data_path = '..//data_files/workbench'

#%%
# Survey Metadata file
metadata = join(data_path, "survey.yml")

# Establish survey instance
survey = gspy.Survey.from_dict(metadata)

#%%
# Create a 'data' branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Make the branch
data_container = survey.gs.add_container('data', **dict(content = "raw data"))

#%%
# Point to Workbench XYZ data files

d_data = join(data_path, 'data//prod_726_729raw_RAW_export.xyz')
d_supp = join(data_path, 'data//raw_data.yml')

# Add the raw AEM data
rd = data_container.gs.add(key='raw_data', data=d_data, metadata_file=d_supp)

#%%
# Create a 'models' branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Make the branch
model_container = survey.gs.add_container('models', **dict(content='inverse models'))

#%%
# Import Workbench XYZ inversion results (syn/dat/inv)

#%%
# GSPy automatically recognizes Workbench inversion files (syn/dat/inv), only
# one of the three files need to be passed to provide the base filename

d_data = join(data_path, 'model//prod_726_729_LBv2_bky_MOD_dat.xyz')
d_supp = join(data_path, 'model//models.yml')

#%%
md = model_container.gs.add(key='inversion', data=d_data, metadata_file=d_supp)

# %%
# Save to NetCDF file
# ^^^^^^^^^^^^^^^^^^^

d_out = join(data_path, 'workbench_example.nc')
survey.gs.to_netcdf(d_out)

#%%
# Inspect survey
# ^^^^^^^^^^^^^^
print(survey.dataset)

#%%
# Inspect the two branches
# ^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Data Branch
print(survey['data'])

#%%
# Models Branch
print(survey['models'])

