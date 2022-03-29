# import os
# from ...utilities import unflatten
# from .Tabular import Tabular
# import xarray as xr

# class Tabular_netcdf(Tabular):

#     def write(self, filename, group='linedata'):
#         """Write the linedata to netcdf file

#         Parameters
#         ----------
#         filename : str
#             Path to the file

#         """
#         mode = 'a' if os.path.isfile(filename) else 'w'

#         self.xarray.to_netcdf(filename, mode=mode, group=group, format='netcdf4', engine='netcdf4')