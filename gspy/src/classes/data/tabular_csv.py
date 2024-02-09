import os
from copy import deepcopy
import json
from pprint import pprint

from numpy import arange, int32
import xarray as xr

from ...utilities.csv_handler import csv_gs
from ...utilities import dump_metadata_to_file
from .Tabular import Tabular

from xarray import register_dataset_accessor

@register_dataset_accessor("gs_tabular_csv")
class Tabular_csv(Tabular):
    """Class to handle tabular csv files.

    ``Tabular_csv.read(filename, metadata_file, spatial_ref, **kwargs)``

    Parameters
    ----------
    filename : str
        Filename to read from.
    metadata_file : str, optional
        Json file name, by default None
    spatial_ref : dict, gspy.Spatial_ref, or xarray.DataArray, optional
        Spatial ref object, by default None

    Returns
    -------
    xarray.Dataset
        Dataset with all data read in.

    See Also
    --------
    Tabular.read : Class method for reading file into class
    ..survey.Spatial_ref : For Spatial reference instantiation.

    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def file_handler(self):
        return csv_gs

    @staticmethod
    def get_attrs(file_handle, variable, **kwargs):
        assert all([x in kwargs for x in ('long_name', 'standard_name', 'null_value', 'units')]), ValueError("Must have at least 'long_name', 'standard_name', 'null_value', 'units'")
        return kwargs

    @staticmethod
    def _create_variable_metadata_template(filename, columns, template_filename=None, **kwargs):
        """Generates a template metadata file.

        The generated file contains gspy required entries in a metadata file for all unique header names in the csv file.

        * standard_name
        * long_name
        * units
        * null_value

        Parameters
        ----------
        filename : str
            Generate a template for this csv file.

        Raises
        ------
        ValueError : When the csv metadata file does not contain entries for each csv column.

        """
        template = {"standard_name": "not_defined",
                    "long_name": "not_defined",
                    "null_value": "not_defined",
                    "units": "not_defined"}

        tmp_dic = {'variable_metadata':{}}
        columns = sorted(list(columns))
        for var in columns:
            tmp_dic['variable_metadata'][var] = template

        if template_filename is None:
            template_filename = "variable_metadata_template_{}.json".format(filename.split(os.sep)[-1].split('.')[0])

        dump_metadata_to_file(tmp_dic, template_filename)

        s = ("\nVariable metadata values are not defined in the metadata file.\n"
               "Creating a template with filename {}\n"
               "Please fill out and add the dictionary to the metadata file.\n").format(template_filename)

        raise Exception(s)

    def write_csv(self, filename):
        """Export tabular_csv to CSV file

        Parameters
        ----------
        filename : str
            Path to output csv file

        """
        tmpdf = self.xr_to_dataframe()
        tmpdf.to_csv(filename, index=None)
