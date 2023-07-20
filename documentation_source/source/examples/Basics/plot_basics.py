
"""
Do Stuff
--------

"""
#%%
import matplotlib.pyplot as plt
from os.path import join
import numpy as np
from gspy import DataArray_gs
from gspy import Coordinate_gs

x = DataArray_gs.from_values('test', np.arange(10), dimensions=None, coords=None)

print(x)

y = Coordinate_gs.from_values('coord', np.arange(0, 100, 2), dimensions=None, coords=None)

print(y)