from os.path import isfile, splitext
from .aseg_gdf_handler import aseg_gdf2_handler
from .csv_handler import csv_handler
from .loupe_handler import loupe_handler

from .xyz_handler import xyz_handler
from .workbench_handler import workbench_handler, workbench_model_handler

def file_handler(filename, **kwargs):

    if "file_type" in kwargs:
        match kwargs['file_type'].lower():
            case 'loupe':
                return loupe_handler
            case 'csv':
                return csv_handler
            case 'aseg':
                return aseg_gdf2_handler
            case 'xyz':
                return xyz_handler
            case 'workbench':
                return workbench_handler

    file_name, file_extension = splitext(filename)
    file_extension = file_extension.lower()

    # Detect data type using file extensions.
    # Aseg .dat comes with a .dfn file
    # Loupe .dat comes with a .desc file
    # XYZ might be Workbench

    wb_handle = None
    if file_extension == '.xyz':

        if xyz_handler.is_workbench_model(filename):
            return workbench_model_handler
        elif xyz_handler.is_workbench(filename):
            return workbench_handler

        # return generic_xyz_handler. when we have it.

        assert False, Exception("Unrecognized XYZ file type.")

    elif file_extension == '.dat':
        if isfile(file_name+'.dfn'):
            return aseg_gdf2_handler
        elif isfile(file_name+file_extension+'.desc'):
            return loupe_handler

    # Catch all others as a csv i.e. .xyz, .csv
    return csv_handler