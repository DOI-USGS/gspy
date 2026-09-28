from .gs_datatree.Survey import Survey
from .gs_dataset.Dataset import Dataset
from .gs_dataset.System import System
from .metadata.Metadata import Metadata

from xarray import open_datatree as xr_open_datatree
from xarray import open_dataset as xr_open_dataset

from ._version import __version__
from .utilities.encoding import restore_fill_values, restore_placeholders, unmasked

def open_datatree(*args, **kwargs):
    kwargs['decode_times'] = kwargs.get('decode_times', False)
    kwargs['decode_cf'] = kwargs.get('decode_cf', True)
    kwargs['format'] = kwargs.get('format', 'NETCDF4')
    kwargs['engine'] = kwargs.get('engine', 'h5netcdf')

    tree = xr_open_datatree(*args, **unmasked(args[0] if args else kwargs.get('filename_or_obj'), kwargs))
    for node in tree.subtree:
        restore_placeholders(node.variables.values())
        restore_fill_values(node.variables.values())
    return tree

def open_dataset(*args, **kwargs):
    kwargs['decode_times'] = kwargs.get('decode_times', False)
    kwargs['decode_cf'] = kwargs.get('decode_cf', True)
    kwargs['format'] = kwargs.get('format', 'NETCDF4')
    kwargs['engine'] = kwargs.get('engine', 'h5netcdf')

    dataset = xr_open_dataset(*args, **unmasked(args[0] if args else kwargs.get('filename_or_obj'), kwargs))
    restore_placeholders(dataset.variables.values())
    restore_fill_values(dataset.variables.values())
    return dataset

def write_ncml(nc_filename, *args, **kwargs):

    ds = open_datatree(nc_filename, *args, **kwargs)['survey']

    ds.gs.write_ncml(nc_filename)