"""
Plot Tabular Examples
-------------------------
Dataset Reference:
Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological Survey data release, https://doi.org/10.5066/P9E44CTQ.

"""
#%%
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from os.path import join
import numpy as np
from gspy import Survey
import xarray as xr
import pyproj

#%%
# Read in Data & Plot
# +++++++++++++++++++

# Path to example files
data_path = '..//..//supplemental//'

# Read in ASEG data file
data_file = data_path + 'region//MAP//data//Tempest.nc'
survey = Survey.open_netcdf(data_file)

# Plot a map of the scattered data points
plt.figure()
gs=gridspec.GridSpec(1,1)
gs.update(bottom=0.12, top=0.98, left=0.2, right=0.98)
survey.tabular[0].gs_tabular.scatter('GPS_Elevation', ax=plt.subplot(gs[0,0]))

#%%

# # Subset by line number
# newld = survey.tabular[0].subset('Line', 225401)
# # Plot the single line in map view
# plt.figure()
# gs=gridspec.GridSpec(1,1)
# gs.update(bottom=0.12, top=0.98, left=0.2, right=0.98)
# newld.scatter('GPS_Elevation', ax=plt.subplot(gs[0,0]))

#%%
# Plotting

# # Plot data channels
# fig = plt.figure(figsize=(8,6))
# gs=gridspec.GridSpec(4,1)
# gs.update(bottom=0.12, top=0.98, left=0.15, right=0.98, hspace=0.5)
# ax0=plt.subplot(gs[0,0])
# newld.plot('X_Powerline', color='b', label='X')
# newld.plot('Z_Powerline', color='r', label='Z')
# plt.ylabel('Powerline')
# plt.legend(loc=2, ncol=2)

# ax1=plt.subplot(gs[1,0])
# newld.plot('RMI', color='limegreen')

# ax2=plt.subplot(gs[2,0])
# newld.plot('EMX_HPRG')

# ax3=plt.subplot(gs[3,0])
# newld.plot('EMZ_HPRG');

plt.show()