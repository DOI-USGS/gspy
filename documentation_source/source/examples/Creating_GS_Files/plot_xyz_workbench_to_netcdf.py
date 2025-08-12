"""

"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
import gspy

#%%
# Convert the ASEG data to NetCDF
# +++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//..//..//example_material//example_4'

# Survey Metadata file
metadata = join(data_path, "survey.yml")

# Establish survey instance
survey = gspy.Survey.from_dict(metadata)

#%%
# 1. Raw Data -
data_container = survey.gs.add_container('data', **dict(content = "raw and processed data"))

# Import raw AEM data from ASEG-format.
# Define input data file and associated metadata file
d_data = join(data_path, 'data//prod_726_729raw_RAW_export.xyz')
d_supp = join(data_path, 'data//raw_data.yml')

# Add the raw AEM data as a tabular dataset
rd = data_container.gs.add(key='raw_data', data_filename=d_data, metadata_file=d_supp)

print(rd)