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

    def __init__(self):
        self._dataset = None
        self._system = {}

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

        system = kwargs.pop('system', None)

        # READ THE SYSTEM FIRST
        if system is None:
            self.add_system(**kwargs)
        self._system = system


        if data_filename is None:
            self._dataset = Raster.read(metadata_file=metadata_file, spatial_ref=spatial_ref, **kwargs)
        else:
            from . import tabular_aseg
            from . import tabular_csv

            file_name, file_extension = os.path.splitext(data_filename)

            json_md = load_metadata_from_file(metadata_file)
            if file_extension == '.dat':
                if os.path.isfile(file_name+'.dfn'):
                    data = tabular_aseg.Tabular_aseg.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, system=system, **kwargs)
                else:
                    file_extension = '.csv'

            if file_extension == '.csv':
                data = tabular_csv.Tabular_csv.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, system=system, **kwargs)

            self._dataset = data

            # HOW DO WE PASS CDs FROM THE SYSTEM TO THE READ METHODS OF THE DATA.



            if self.system is not None:
                for key, value in self.system.items():
                    if value.attrs['method'] == self.dataset.attrs['method']:
                        value.gs_system.check_against_data(self.dataset)

                        # We need to add the coordinate dimensions pf the gatetimes from the data to the system



        if self.system is None:
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

    def system_present(self, **kwargs):
        return any(['system' in x for x in list(kwargs.keys())])

    @classmethod
    def open_netcdf(cls, filename, **kwargs):

        self = cls()
        self._dataset = Dataset.open_netcdf(filename, **kwargs)

        survey/walktem_40m/system
        survey/walktem_100m/system

        try:
            self._system = Dataset.open_netcdf(filename, group=kwargs.pop('group')+'/system', **kwargs)
            return self
        except:
            return self.dataset

    def write_netcdf(self, filename, group):

        self._dataset.gs_dataset.write_netcdf(filename, group)

        if self.system is not None:
            self._system.gs_dataset.write_netcdf(filename, group+'/system')