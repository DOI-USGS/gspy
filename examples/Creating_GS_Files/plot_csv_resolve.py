"""
CSV to NetCDF (RESOLVE AEM)
---------------------------

This example demonstrates how to convert comma-separated values (CSV) data to the GS NetCDF format. Specifically this example includes:

1. Raw AEM data, from the Resolve system
2. Inverted resistivity models

Dataset Reference: `Burton, B.L., Minsley, B.J., Bloss, B.R., Rigby, J.R., Kress, W.H., and Smith, B.D., 2019, Airborne electromagnetic, magnetic, and radiometric survey, Shellmound, Mississippi, March 2018 (ver. 2.0, March 2024): U.S. Geological Survey data release, https://doi.org/10.5066/P9D4EA9W.`

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy
from gspy.metadata.Metadata import Metadata


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
# Create a 'data' branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Make the branch
data_container = survey.gs.add_container('data', **dict(content = "raw and processed data"))

#%%
# Point to data CSV file

# Define input data file and associated metadata file
d_data = join(data_path, 'data//Resolve.csv')

#%%
# Point to MULTIPLE metadata files (YAML & CSV)

# metadata about the dataset and systems in YAML format
d_supp = join(data_path, 'data//Resolve_data_md_without_variables.yml')

# variable-specific metadata in a CSV Data Dictionary format
var_meta = join(data_path, 'data//Resolve_DataDictionary_md.csv')

# merge the two metadata and pass it all through for the raw AEM data
md = Metadata.merge(Metadata.read(d_supp), Metadata.read(var_meta, usgs=True))

# Add the raw AEM data
rd = data_container.gs.add(key='raw_data', data_filename=d_data, metadata_file=md)

#%%
# Create a 'models' branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Import inverted AEM models from CSV-format.
model_container = survey.gs.add_container('models', **dict(content = "inverted models"))

#%%
# Define input model file and associated metadata file
m_data = join(data_path, 'model//Resolve_model.csv')
m_supp = join(data_path, 'model//Resolve_model_md.yml')

#%%
# Add the inverted AEM models as a tabular dataset
mod_branch = model_container.gs.add(key="model", data_filename=m_data, metadata_file=m_supp)

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
new_survey['models/model'].gs.scatter(hue='doi_standard')
plt.show()
