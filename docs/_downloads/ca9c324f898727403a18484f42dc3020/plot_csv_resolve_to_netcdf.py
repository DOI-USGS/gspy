"""
CSV to NetCDF
-------------

This example demonstrates how to convert comma-separated values (CSV) data to the GS NetCDF format. Specifically this example includes:

1. Raw AEM data, from the Resolve system
2. Inverted resistivity models

Dataset Reference:
Burton, B.L., Minsley, B.J., Bloss, B.R., and Kress, W.H., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2018 - February 2019: U.S. Geological Survey data release, https://doi.org/10.5066/P9XBBBUU.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy

#%%
# Convert the resolve csv data to NetCDF
# ++++++++++++++++++++++++++++++++++++++

#%%
# Initialize the Survey

# Path to example files
data_path = '..//..//..//..//example_material//example_2'

# Survey metadata file
metadata = join(data_path, "data//Resolve_survey_md.yml")
# Establish the Survey
survey = gspy.Survey.from_dict(metadata)

#%%
# Import raw AEM data from CSV-format.

data_container = survey.gs.add_container('data', **dict(content = "raw and processed data"))

# Define input data file and associated metadata file
d_data = join(data_path, 'data//Resolve.csv')
d_supp = join(data_path, 'data//Resolve_data_md.yml')

# Add the raw AEM data as a tabular dataset
data_container.gs.add(key='raw_data', data_filename=d_data, metadata_file=d_supp)

#%%
# Import inverted AEM models from CSV-format.

model_container = survey.gs.add_container('models', **dict(content = "inverted models"))

# Define input model file and associated metadata file
m_data = join(data_path, 'model//Resolve_model.csv')
m_supp = join(data_path, 'model//Resolve_model_md.yml')

# Add the inverted AEM models as a tabular dataset
model_container.gs.add(key="model", data_filename=m_data, metadata_file=m_supp)

#%%
# Save to NetCDF file
d_out = join(data_path, 'model//Resolve.nc')
survey.gs.to_netcdf(d_out)

#%%
# Reading back in the GS NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

# Check the Survey information
#%%
# Plotting

# Make a scatter plot of a specific data variable, using GSPy's plotter
plt.figure()
new_survey['data/raw_data'].gs.scatter(hue='dtm', vmin=30, vmax=50)

# Subsetting by line number, and plotting by distance along that line
tmp = new_survey['data/raw_data'].gs.subset('line', 10010)
# tmp = new_survey['data'].where(new_survey['data'].dataset['line']==10010)
plt.figure()
# plt.subplot(121)
# tmp.gs_tabular.plot(hue='DTM')
# plt.subplot(122)
# tmp.gs_tabular.scatter(x='x', y='DTM')
tmp.gs.scatter(y='dtm')

#IF YOU SPECIFY HUE ITS A 2D COLOUR Plot
#OTHERWISE ITS JUST A PLOT (LINE POINTS ETC)

# Make a scatter plot of a specific model variable, using GSPy's plotter
plt.figure()
new_survey['models/model'].gs.scatter(hue='doi_standard')
plt.show()
