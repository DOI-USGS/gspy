"""
ASEG-GDF (Tempest AEM)
----------------------

This example demonstrates the workflow for creating a GS file from the `ASEG <https://www.aseg.org.au/sites/default/files/pdf/ASEG-GDF2-REV4.pdf>`_ file format, as well as how to add multiple associated datasets to the Survey. Specifically, this AEM survey contains the following datasets:

1. Raw AEM data, from the Tempest system
2. Inverted resistivity models
3. An interpolated map of total magnetic intensity

Source Reference: Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""

# sphinx_gallery_thumbnail_number = 3

#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = "../data_files/tempest_aseg"

# Survey Metadata file
metadata = join(data_path, "data", "Tempest_survey_md.yml")

# Establish survey instance
survey = gspy.Survey.from_dict(metadata)

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/data/Tempest_survey_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Survey YAML file
#

#%%
# Create a branch and attach data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#%%
# Create the first branch (container) called "data"
data_container = survey.gs.add_container('data', **dict(content = "raw data"))

#%%
# 1. Raw Data

#%%
# Import raw AEM data from ASEG-GDF2 format.

d_data = join(data_path, 'data', 'Tempest.dat')
d_supp = join(data_path, 'data', 'Tempest_data_md.yml')

# Add the raw AEM data to the data branch
rd = data_container.gs.add(key='raw_data',
                           data=d_data,
                           metadata_file=d_supp)

#%%
# Note for ASEG-GDF2 files, variable metadata is pulled directly from the DFN file associated with the DAT file. Any additional variable metadata, or desired overwrites to the DFN values, can be passed through the YAML.

#%%
# In this example, multiple systems are defined in the Tempest_data_md.yml metadata file:

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/data/Tempest_data_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Raw Data YAML file
#

#%%
# Create a 2nd branch and attach model data leaves
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

model_container = survey.gs.add_container('models', **dict(content = "inverted 1-D electrical resistivity models"))

# Define Path to inverted AEM models and corresponding metadata file
m_data = join(data_path, 'model', 'Tempest_model.dat')
m_supp = join(data_path, 'model', 'Tempest_model_md.yml')

# Add models to the model container, note this example contains a "parameters" group that
# is added as a leaflet below the model group.
mod = model_container.gs.add(key='inverted_models',
                             data=m_data,
                             metadata_file=m_supp,
                             system=rd.tempest_system,
                             derived_from=rd)

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/model/Tempest_model_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Inverted Model YAML file
#

#%%
# Create a 3rd branch for the magnetic intensity map
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# Create a new branch for the contractor-derived total magnetic intensity map
map_container = survey.gs.add_container('derived_maps', **dict(content = "derived maps"))

# Import the magnetic data from TIF-format.
d_supp = join(data_path, 'data', 'Tempest_raster_md.yml')

# Add the magnetic map to the data
maps = map_container.gs.add(key='maps', metadata_file = d_supp)

#%%
# Note: raster data files are defined within the metadata file

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/data/Tempest_raster_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Magnetic Raster Map YAML file
#

#%%
# Save NetCDF file
# ^^^^^^^^^^^^^^^^

d_out = join(data_path, 'Tempest.nc')
survey.gs.to_netcdf(d_out)

#%%
#Read back in the NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

#%%
# View the Data Tree
# ^^^^^^^^^^^^^^^^^^
print(new_survey.gs.tree)
print(new_survey)

#%%
# The scalar variables that print as an empty ``float64`` NaN, such as
# ``survey_information`` or ``flightline_information``, are not missing data.
# netCDF cannot hold nested attributes, so each metadata block is attached to
# one of these placeholder variables. In a Jupyter notebook, displaying the
# survey without ``print`` gives xarray's tree view, where each block's fields
# are listed inline; the workshop notebooks use that style throughout.

#%%
# Once the survey is read in, we can access variables like a standard xarray dataset.

#%%
# Option A:
print(new_survey['derived_maps/maps'].magnetic_tmi)
#%%
# Option B:
print(new_survey['derived_maps/maps']['magnetic_tmi'])

#%%
# Option C:
print(new_survey['derived_maps']['maps']['magnetic_tmi'])

# %%
# Plotting Examples
# ^^^^^^^^^^^^^^^^^
# demonstrating different ways to access and plot variables

# A line profile of one variable along a flight line. The data hold a single
# line here, so we subset by it anyway and put the line number in the title.
line = int(new_survey['data']['raw_data']['line'].values[0])
subset = new_survey['data']['raw_data'].gs.subset('line', line)

plt.figure()
subset.gs.plot('tmi', x='distance')
plt.title(f"Line {line}")
plt.tight_layout()

#%%
# A map view of the flight path, coloured by a tabular variable, using GSPy's
# plotter. The 'y' coordinate is used automatically, so it is never named in
# the call; axis and colorbar labels are built from the variable metadata.
plt.figure()
new_survey['data']['raw_data'].gs.scatter(x='x', hue='tx_height', cmap='jet')

#%%
# A map view of a raster variable, using xarray's plotter. The title is set
# explicitly because xarray otherwise fills it from the leftover scalar
# coordinate 'spatial_ref', which carries no information.
# HT
plt.figure()
new_survey['derived_maps/maps']['magnetic_tmi'].plot(cmap='jet', robust=True)
plt.suptitle("Total magnetic intensity")
plt.show()