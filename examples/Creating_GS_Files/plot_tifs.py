"""
GeoTIFFs (2D & 3D)
------------------

In this example, we demonstrate the workflow for creating a GS file from the GeoTIFF (.tif/.tiff) file format. This includes adding individual TIF files as single 2-D variables, as well as how to create a 3-D variable by stacking multiple TIF files along a specified dimension.

The GS standard requires a single set of ``x``, ``y``, ``z``, ``t`` coordinate variables per data leaf group. Therefore, this example also shows how tifs with differing x-y grids need to be added to separate groups, and all variables in a group should have matching coordinates:

1. Raster Dataset #1
    - 2-D magnetic grid, original x-y discretization (600 m cell size)
2. Raster Dataset #2
    - 2-D magnetic grid, aligned to match the x-y dimensions of the resistivity layers (1000 m cell size)
    - 3-D resistivity grid

Lastly, GSPy provides a "to_tif()" method to export raster data as GeoTIFF. This example demonstrates how to use this method for both 2D and 3D variables.

Source References: 

Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

James, S.R., and Minsley, B.J., 2021, Combined results and derivative products of hydrogeologic structure and properties from airborne electromagnetic surveys in the Mississippi Alluvial Plain: U.S. Geological Survey data release, https://doi.org/10.5066/P9382RCI.

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy
from gspy import Survey

#%%
# Initialize the Survey
# ^^^^^^^^^^^^^^^^^^^^^

# Path to example files
data_path = "..//data_files//tempest_aseg"

# Survey metadata file
metadata = join(data_path, "data//Tempest_survey_md.yml")

# Establish the Survey
survey = Survey.from_dict(metadata)

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/data/Tempest_survey_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Survey YAML file
#

#%%
# Create a branch for all maps
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

container = survey.gs.add_container('derived_products',
                                    **dict(content = "container of gridded maps of magnetic and electrical resistivity values",
                                           comment = "Magnetic map is contractor-derived, resistivity maps are USGS-derived"))

#%%
# Attach the 2D Magnetic Raster Dataset (600 m cell size)
# """""""""""""""""""""""""""""""""""""""""""""""""""""""

#%%
# Define input metadata file, which contains the TIF filename linked 
# with desired variable name and info. 

d_supp1 = join(data_path, 'data//Tempest_raster_md.yml')

# Attach the magnetic map to the container
mm = container.gs.add(key="mag_map", metadata_file=d_supp1)

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/data/Tempest_raster_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Magnetic raster (600 m cell size) YAML file
#

#%%
# Attach 3D Resistivity Grids + Aligned 2D Magnetic Raster (1000 m cell size)
# """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

#%%
# Import both 3-D resistivity and 2-D magnetic data, aligned onto a common 1000 m x 1000 m grid
d_supp2 = join(data_path, 'data//Tempest_rasters_md.yml')

# Attach rasters to the container
rm = container.gs.add(key="all_maps", metadata_file=d_supp2)

#%%
#
# .. literalinclude:: /../../examples/data_files/tempest_aseg/data/Tempest_rasters_md.yml
#    :language: yaml
#    :linenos:
#    :caption: Resistivity & Magnetic grids (1000 m cell size) YAML file
#

#%%
# Note: the stack dimension is defined as "depth" but for the resistivity variable 
# the dimensions are listed as [x, y, z] ... this is because under coordinates
# we are linking the `z` coordinate dimension to the incoming depth dimension. 
# Therefore the name "depth" ends up not getting used because that dimension becomes
# "z" instead.

#%%
# Inspect the data tree
# ^^^^^^^^^^^^^^^^^^^^^
print(survey)

# %%
# Save to NetCDF file
# ^^^^^^^^^^^^^^^^^^^
d_out = join(data_path, 'tifs.nc')
survey.gs.to_netcdf(d_out)

#%%
# Option 1: 
#
# Pass a variable name to export just that variable
survey['derived_products']["all_maps"].gs.to_tif('magnetic_tmi')

#%%
# Option 2: 
# 
# Export all the variables by NOT passing any variable names,
# but need to specify a slice dimension for the 3D resistivity variable.
# Can optionally pass a directory path to export tiffs to.
survey['derived_products']["all_maps"].gs.to_tif(slice_dim='z', out_dir=data_path)

#%%
# Reading back in the GS NetCDF file
new_survey = gspy.open_datatree(d_out)['survey']

#%%
# Plotting

#%%
# Make a map-view plot of a specific data variable, using Xarray's plotter
# In this case, we slice the 3-D resistivity variable along the depth dimension

r_plot = new_survey['derived_products']["all_maps"]['resistivity'].plot(col='z', vmax=3, cmap='jet', robust=True)

#%%
# Make a map-view plot comparing the different x-y discretization of the two magnetic variables, using Xarray's plotter
plt.figure()
ax=plt.gca()
plot1 = new_survey['derived_products']["all_maps"]['magnetic_tmi'].plot(ax=ax, cmap='jet', vmin=0, vmax=1000, robust=True)
plot2 = new_survey['derived_products']["mag_map"]['magnetic_tmi'].plot(ax=ax, cmap='Greys', cbar_kwargs={'label': ''}, robust=True)
plt.ylim([1.20556e6, 1.21476e6])
plt.xlim([3.5201e5, 3.6396e5])
plt.show()
