"""
CSV (Resolve AEM)
-----------------

This example demonstrates how to convert comma-separated values (CSV) data to the GS NetCDF format. Specifically this example includes:

1. Raw data

    - electromagnetic data, Resolve frequency-domain airborne electromagnetic (AEM) data
    - magnetic data
    - radiometric data

2. Inverted resistivity models

This example also demonstrates how to read metadata from different formats (YAML and CSV), and includes examples of electromagnetic, magnetic, and radiometric systems.

Source Reference: Burton, B.L., Minsley, B.J., Bloss, B.R., Rigby, J.R., Kress, W.H., and Smith, B.D., 2019, Airborne electromagnetic, magnetic, and radiometric survey, Shellmound, Mississippi, March 2018 (ver. 2.0, March 2024): U.S. Geological Survey data release, https://doi.org/10.5066/P9D4EA9W.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy
from gspy.metadata.Metadata import Metadata
from pprint import pprint

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = '..//data_files//resolve'

# Survey metadata file
metadata = join(data_path, "data//Resolve_survey_md.yml")

# Establish the Survey
survey = gspy.Survey.from_dict(metadata)

#%%
#
# .. literalinclude:: /../../examples/data_files/resolve/data/Resolve_survey_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Survey YAML file
#

#%%
# Create a 'data' branch
# ^^^^^^^^^^^^^^^^^^^^^^

#%%
# Make the branch
data_container = survey.gs.add_container('data', **dict(content = "raw and processed data"))

#%%
# Point to raw data CSV file

# Define input data file and associated metadata file
d_data = join(data_path, 'data//Resolve.csv')

#%%
# Multiple Geophysical Systems & Metadata Formats
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Import from MULTIPLE metadata files (YAML & CSV)
# """"""""""""""""""""""""""""""""""""""""""""""""

#%%
# Metadata about the dataset and systems are in YAML format

d_supp = join(data_path, 'data//Resolve_data_md_without_variables.yml')
rd_meta = Metadata.read(d_supp)

#%%
#
# .. literalinclude:: /../../examples/data_files/resolve/data/Resolve_data_md_without_variables.yml
#    :language: yaml
#    :linenos:
#    :caption: Raw Data YAML file (missing variable metadata!)
#

#%%
# Variable metadata are in a CSV table

#%%
# Pass the flag 'table=True' for this specific metadata format

var_md = join(data_path, 'data//Resolve_variable_table_md.csv')
var_meta = Metadata.read(var_md, table=True)

#%%
# (scroll left right to see the full table)

#%%
# 
# .. csv-table:: Variable Metadata in CSV table format
#    :file: /../../examples/data_files/resolve/data/Resolve_variable_table_md.csv
#    :header-rows: 1
#    :widths: 10 10 10 10 10 10 10 10 10 10 10
#    :class: leftcap
# 

#%%
# Merge the two metadata and pass it all through for the raw AEM data. 
md = Metadata.merge(rd_meta, var_meta)

# Add the raw AEM data
rd = data_container.gs.add(key='raw_data', data_filename=d_data, metadata_file=md)

#%%
# View the merged Metadata to see how the information was imported

#%%
pprint(md)

#%%
# Create a 'models' branch 
# ^^^^^^^^^^^^^^^^^^^^^^^^

#%%
model_container = survey.gs.add_container('models', **dict(content = "inverted models"))

#%%
# Define input model file
m_data = join(data_path, 'model//Resolve_model.csv')

#%%
# Continue exploring different Metadata options
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Once again, read partial metadata from YAML

m_supp = join(data_path, 'model//Resolve_model_md.yml')
md_meta = Metadata.read(m_supp)

#%%
#
# .. literalinclude:: /../../examples/data_files/resolve/model/Resolve_model_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Model YAML file (missing variable metadata!)
#

#%%
# ... and read remaining metadata from CSV table

mod_var_md = join(data_path, 'model//Resolve_model_variable_table_md.csv')
mod_var_meta = Metadata.read(mod_var_md, table=True)

#%%
# (scroll left right to see the full table)

#%%
# 
# .. csv-table:: Model Variable Metadata in CSV table format
#    :file: /../../examples/data_files/resolve/model/Resolve_model_variable_table_md.csv
#    :header-rows: 1
#    :widths: 10 10 10 10 10 10 10 10 10 10 10
#    :class: leftcap
# 

#%%
# Merge the two metadata
mod_md = Metadata.merge(md_meta, mod_var_meta)

#%%
# Export Metadata to EXCEL or CSV
# """""""""""""""""""""""""""""""

#%%
# GSPy supports metadata from Microsoft excel files, 
# which can optionally be saved as CSV. This structure 
# matches the YAML heiararchical dictionary format and 
# is distinct from the variable metadata table (.csv but table=True) shown above. 

mod_md.dump(join(data_path, 'model//Resolve_model_md.csv'))
mod_md.dump(join(data_path, 'model//Resolve_model_md.xlsx'))

#%%
# 
# .. csv-table:: Model Metadata (ALL) in EXCEL/CSV format
#    :file: /../../examples/data_files/resolve/model/Resolve_model_md.csv
#    :header-rows: 0
#    :widths: 10 10 10 10 10
#    :class: leftcap
# 

#%%
# Add the inverted AEM models with combined metadata dictionary
mod_branch = model_container.gs.add(key="inverted_models", data_filename=m_data, metadata_file=mod_md)

#%%
# Inspect the two branches
# ^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Data Branch
print(survey['data'])

#%%
# Models Branch
print(survey['models'])

# %%
# Save to NetCDF file
# ^^^^^^^^^^^^^^^^^^^
d_out = join(data_path, 'Resolve.nc')
survey.gs.to_netcdf(d_out)

#%%
# Reading back in the GS NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

# %%
# Plotting
# ^^^^^^^^

# Make a scatter plot of a specific data variable, using GSPy's plotter
plt.figure()
new_survey['data/raw_data'].gs.scatter(hue='z', vmin=30, vmax=50)

# %%
# Subsetting by line number and plot by distance along line
subset = new_survey['data/raw_data'].gs.subset('line', 10010)

plt.figure()
_ = subset.gs.scatter(y='z', x='distance')

# %%
# Make a scatter plot of a specific model variable, using GSPy's plotter
plt.figure()
new_survey['models/inverted_models'].gs.scatter(hue='doi_standard')
plt.show()
