from os.path import isfile, splitext
from .aseg_gdf_handler import aseg_gdf2_handler
from .csv_handler import csv_handler
from .loupe_handler import loupe_handler

def file_handler(filename):

    file_name, file_extension = splitext(filename)
    file_extension = file_extension.lower()

    if file_extension == '.csv':
        return csv_handler
    elif file_extension == '.dat':
        if isfile(file_name+'.dfn'):
            return aseg_gdf2_handler
        elif isfile(file_name+file_extension+'.desc'):
            return loupe_handler
        else:
            return csv_handler