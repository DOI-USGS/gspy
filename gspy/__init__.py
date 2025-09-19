from .gs_datatree.Survey import Survey
from .gs_dataset.Dataset import Dataset
from .gs_dataset.System import System

from xarray import open_datatree as xr_open_datatree
from xarray import open_dataset as xr_open_dataset

def open_datatree(*args, **kwargs):
    kwargs['decode_times'] = kwargs.get('decode_times', False)
    kwargs['decode_cf'] = kwargs.get('decode_cf', True)
    kwargs['format'] = kwargs.get('format', 'NETCDF4')
    kwargs['engine'] = kwargs.get('engine', 'h5netcdf')

    return xr_open_datatree(*args, **kwargs)

def open_dataset(*args, **kwargs):
    kwargs['decode_times'] = kwargs.get('decode_times', False)
    kwargs['decode_cf'] = kwargs.get('decode_cf', True)
    kwargs['format'] = kwargs.get('format', 'NETCDF4')
    kwargs['engine'] = kwargs.get('engine', 'h5netcdf')

    return xr_open_dataset(*args, **kwargs)

def write_ncml(nc_filename, *args, **kwargs):

    ds = open_datatree(nc_filename, *args, **kwargs)['survey']

    ds.gs.write_ncml(nc_filename)