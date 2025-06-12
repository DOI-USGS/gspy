"""
Plotting Cross Sections
-----------------------

"""

import numpy as np
import matplotlib.pyplot as plt
from os.path import join
import gspy
from gspy import Survey
from pprint import pprint

#%%
# First Create the Survey & Data Objects

# Initialize the Survey
data_path = '..//..//..//..//example_material//example_2/data'

survey = gspy.open_datatree(join(data_path, "Tempest.nc"))['survey']

plt.figure()
survey['models/inverted_models'].gs.plot_cross_section(line_number=212201,
                                                                    variable='conductivity',
                                                                    hang_from=None,
                                                                    axis='distance',
                                                                    equalize=True,
                                                                    log=10,
                                                                    cmap='jet',
                                                                    ylim=[-200, 100.0])

plt.figure()
survey['models/inverted_models'].gs.plot_cross_section(line_number=212201, variable='conductivity', hang_from='elevation', axis='distance', equalize=True, log=10, cmap='jet', ylim=[-200, 100.0])
plt.show()