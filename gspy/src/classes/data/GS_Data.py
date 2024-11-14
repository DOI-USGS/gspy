import os
from copy import deepcopy
from pprint import pprint
import xarray as xr
from netCDF4 import Dataset as ncdf4_Dataset
import h5py

from .xarray_gs.Dataset import Dataset
from .Tabular import Tabular
from .Raster import Raster
from .System import System
from ...utilities import flatten, dump_metadata_to_file, load_metadata_from_file

import xarray as xr

class GS_Data(object):
    """Class defining a survey or dataset
    """

    def __init__(self, dataset=None, system={}):
        self._dataset = dataset
        self._system = system

    @property
    def dataset(self):
        return self._dataset

    @property
    def system(self):
        return self._system

    def __getitem__(self, value):
        if self.system is not None:
            return self.dataset[value]

    @classmethod
    def read(cls, data_filename=None, metadata_file=None, spatial_ref=None, **kwargs):

        self = cls()

        json_md = load_metadata_from_file(metadata_file)

        system = kwargs.get('system', None)

        # READ THE SYSTEM FIRST
        if system is None:
            for key in list(json_md.keys()):
                if "system" in key:
                    if system is None:
                        system = {}
                    value = json_md.pop(key)
                    system[key] = System.from_dict(**value)

        # Attach apriori given system dict
        kwargs['system'] = system

        if data_filename is None:
            self._dataset = Raster.read(metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)
        else:
            from . import tabular_aseg
            from . import tabular_csv

            file_name, file_extension = os.path.splitext(data_filename)

            if file_extension == '.dat':
                if os.path.isfile(file_name+'.dfn'):
                    data = tabular_aseg.Tabular_aseg.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)
                else:
                    file_extension = '.csv'

            if file_extension == '.csv':
                data = tabular_csv.Tabular_csv.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)

            self._dataset = data
            if system is not None:
                self._system = system

        if len(self.system) == 0:
            return self.dataset
        else:
            return self

    def add_system(self, **kwargs):
        # Pop system(s) information from the metadata
        for key in list(kwargs.keys()):
            if "system" in key:
                value = kwargs.pop(key)
                self._system[key] = System.from_dict(**value)

        return kwargs

    def scatter(self, *args, **kwargs):
        return self.dataset.gs_tabular.scatter(*args, **kwargs)

    def subset(self, key, value):
        return type(self)(self.dataset.where(self.dataset[key]==value), self.system)

    def system_present(self, **kwargs):
        return any(['system' in x for x in list(kwargs.keys())])

    @classmethod
    def open_netcdf(cls, filename, **kwargs):

        self = cls(dataset=None, system={})

        incoming_handle = 'handle' in kwargs
        handle = kwargs.pop('handle', h5py.File(filename, 'r'))

        self._dataset = Dataset.open_netcdf(filename, **kwargs)

        group = kwargs.pop('group')

        for key in list(handle[group].keys()):
            if '_system' in key:
                self._system[key] = Dataset.open_netcdf(filename, group=f'{group}/{key}', **kwargs)

        if not incoming_handle:
            handle.close()

        if len(self.system) == 0:
            return self.dataset
        else:
            return self

    def write_netcdf(self, filename, group):

        self._dataset.gs_dataset.write_netcdf(filename, group)

        if self.system is not None:
            for key, value in self.system.items():
                value.gs_dataset.write_netcdf(filename, f'{group}/{key}')