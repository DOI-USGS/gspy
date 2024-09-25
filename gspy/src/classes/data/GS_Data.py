import os
from copy import deepcopy
from pprint import pprint
import xarray as xr
from netCDF4 import Dataset as ncdf4_Dataset
import h5py

from .Tabular import Tabular
from .Raster import Raster
from .System import System
from ...utilities import flatten, dump_metadata_to_file, load_metadata_from_file

import xarray as xr

class GS_Data(object):
    """Class defining a survey or dataset
    """

    def __init__(self, metadata=None):
        self._dataset = None
        self._system = None

    @property
    def dataset(self):
        return self._dataset

    @property
    def system(self):
        return self._system

    def check_system_against_data(self):
        """Assert that gate time strings match the coordinates of the attached dataset.
        """
        for gt in self.system['component_gate_times']:
            assert gt in list(self.dataset.coords.keys()), ValueError(f"Could not match component gate times {gt} to dataset coordinates")

    @classmethod
    def read(cls, typ, data_filename, metadata_file=None, spatial_ref=None, **kwargs):

        from . import tabular_aseg
        from . import tabular_csv

        self = cls()
        if typ == 'netcdf':
            self._dataset = Tabular.open_netcdf(data_filename, **kwargs)
            self._system = Tabular.open_netcdf(data_filename, group=kwargs.pop('group')+'/system', **kwargs)
            return self

        json_md = load_metadata_from_file(metadata_file)
        if typ == 'aseg':
            data = tabular_aseg.Tabular_aseg.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)

        elif typ == 'csv':
            data = tabular_csv.Tabular_csv.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)

        self._dataset = data
        self._system = System.add_electromagnetic_system(**json_md['electromagnetic_system'])

        self.check_system_against_data()

        return self

    def write_netcdf(self, filename, group):

        self._dataset.gs_dataset.write_netcdf(filename, group)
        self._system.gs_dataset.write_netcdf(filename, group+'/system')