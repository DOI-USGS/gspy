import os
from copy import deepcopy
import json
from pprint import pprint

from numpy import arange, int32
import xarray as xr


from ...utilities.csv_handler import csv_gs
from .xarray_gs.DataArray_gs import DataArray_gs
from .Tabular import Tabular
from .Variable_Metadata import variable_metadata

class Tabular_csv(Tabular):
    __slots__ = ()
    """Class to handle tabular csv files.

    ``Tabular('csv', data_filename, metadata_file, spatial_ref, **kwargs)``

    See Also
    --------
    gspy.Tabular_csv.read : Class method for reading file into class
    gspy.Tabular : Parent and generic interface.

    """

    @property
    def file_handler(self):
        return csv_gs

    @staticmethod
    def get_attrs(file_handle, variable, **kwargs):
        return kwargs
        # return kwargs[variable]


    # @classmethod
    # def read(cls, filename, metadata_file=None, spatial_ref=None, **kwargs):
    #     """Read a csv file

    #     Parameters
    #     ----------
    #     filename : str
    #         Csv filename to read from.
    #     metadata_file : str, optional
    #         Json file to pull variable metadata from, by default None
    #     spatial_ref : gspy.Spatial_ref, optional
    #         Spatial reference system, by default None

    #     Returns
    #     -------
    #     out : gspy.Tabular
    #         Tabular class with csv data.

    #     See Also
    #     --------
    #     gspy.Spatial_ref : For Spatial reference instantiation.

    #     """

    #     self = cls()

    #     self = self.set_spatial_ref(spatial_ref)

    #     # Read the GSPy json file.
    #     json_md = self.read_metadata(metadata_file)

    #     file = csv_gs.read(filename)

    #     # Add the index coordinate
    #     self = self.add_coordinate_from_values('index',
    #                                            arange(file.df.values.shape[0], dtype=int32),
    #                                            discrete = True,
    #                                            is_dimension=True,
    #                                            **{'standard_name' : 'index',
    #                                               'long_name' : 'Index of individual data points',
    #                                               'units' : 'not_defined',
    #                                               'null_value' : 'not_defined'})

    #     # Add the user defined coordinates-dimensions from the json file
    #     dimensions = json_md['dimensions']
    #     coordinates = json_md['coordinates']
    #     reverse_coordinates = {v:k for k,v in coordinates.items()}

    #     for key in list(dimensions.keys()):
    #         b = reverse_coordinates.get(key, key)
    #         assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
    #         if isinstance(dimensions[key], dict):
    #             # dicts are defined explicitly in the json file.
    #             self = self.add_coordinate_from_dict(b, is_dimension=True, **dimensions[key])

    #     # Write out a template json file when no variable metadata is found
    #     if not 'variable_metadata' in json_md:
    #         # ??? Fix Me
    #         Tabular_csv._create_variable_metadata_template(filename, file.df.columns)

    #     # Add in the spatio-temporal coordinates
    #     for key in list(coordinates.keys()):
    #         coord = coordinates[key].strip()
    #         discrete = key in ('x', 'y', 'z', 't')

    #         dic = json_md['variable_metadata'][coord]

    #         # Might need to handle already added coords from the dimensions dict.
    #         self = self.add_coordinate_from_values(key,
    #                                                file.df[coord].values,
    #                                                dimensions=["index"],
    #                                                discrete = discrete,
    #                                                is_projected = self.is_projected,
    #                                                is_dimension=False,
    #                                                **dic)

    #     # Now we have all dimensions and coordinates defined.
    #     # Start adding the data variables
    #     for var, var_meta in json_md['variable_metadata'].items():
    #         if not var in coordinates.keys():
    #             all_columns = sorted(list(file.df.columns))

    #             # Use a column from the CSV file and add it as a variable
    #             if var in all_columns:
    #                 self.add_variable_from_values(var,
    #                                               file.df[var].values,
    #                                               dimensions = ["index"],
    #                                               **var_meta)

    #             else: # The CSV column header is a 2D variable with [x] in the column name
    #                 column_counts = Tabular_csv.count_column_headers(file.df.columns)

    #                 values = None
    #                 # check for raw_data_columns to combine
    #                 if 'raw_data_columns' in var_meta:
    #                     values = file.df[var_meta['raw_data_columns']].values

    #                 # if variable has multiple columns with [i] increment, to be combined
    #                 elif (var in column_counts) and (column_counts[var] > 1):
    #                     values = file.df[["{}[{}]".format(var, i) for i in range(column_counts[var])]].values

    #                 assert values is not None, ValueError(('{} not in data file, double check, '
    #                                                       'raw_data_columns field required in variable_metadata '
    #                                                       'if needing to combine unique columns to new variable without an [i] increment').format(var))

    #                 assert all([dim in self.dims for dim in var_meta['dimensions']]), ValueError("Could not match variable dimensions {} with json dimensions {}".format(var_meta['dimensions'], self.dims))

    #                 self.add_variable_from_values(var, values, **var_meta)

    #     # add global attrs to tabular, skip variable_metadata and dimensions
    #     self.update_attrs(**json_md['dataset_attrs'])

    #     return self

    @staticmethod
    def _create_variable_metadata_template(filename, columns):
        """Generates a template metadata file.

        The generated file contains gspy required entries in a metadata files; standard_name, long_name, units, null_value.

        Parameters
        ----------
        filename : str
            Generate a template for this csv file.

        Raises
        ------
        ValueError : When the csv metadata file does not contain entries for each csv column.

        """
        tmp_dic = {'variable_metadata':{}}

        columns = sorted(list(columns))

        for var in columns:
            tmp_dic['variable_metadata'][var] = {"standard_name": "not_defined", "long_name": "not_defined", "units": "not_defined", "null_value": "not_defined"}

        out_filename = "variable_metadata_template_{}.json".format(filename.split(os.sep)[-1].split('.')[0])
        with open(out_filename, "w") as f:
            json.dump(tmp_dic, f, indent=4)

        s = ("\nVariable metadata values are not defined in the supplemental information file.\n"
                "Creating a template with filename {}\n"
                "Please fill out and add the dictionary to the supplemental information file.\n").format(out_filename)

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
