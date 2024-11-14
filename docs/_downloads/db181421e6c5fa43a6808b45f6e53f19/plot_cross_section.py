"""
Plotting Cross Sections
-----------------------

"""

import numpy as np
import matplotlib.pyplot as plt
from os.path import join
from gspy import Survey
from pprint import pprint

#%%
# First Create the Survey & Data Objects

# Initialize the Survey
data_path = '..//..//..//..//example_material//example_2/data'

survey = Survey.open_netcdf(join(data_path, "Tempest.nc"))

plt.figure()
ax, pm, cb = survey['model'].gs_tabular.plot_cross_section(line_number=212201, variable='conductivity', hang_from=None, axis='distance', equalize=True, log=10, cmap='jet', ylim=[-200, 100.0])

plt.figure()
_, pm, cb = survey['model'].gs_tabular.plot_cross_section(line_number=212201, variable='conductivity', hang_from='elevation', axis='distance', equalize=True, log=10, cmap='jet', ylim=[-200, 100.0])
plt.show()