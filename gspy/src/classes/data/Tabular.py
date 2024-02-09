import os
import json
import matplotlib.pyplot as plt
from pprint import pprint

import xarray as xr
import numpy as np
from numpy import arange, int32

from .xarray_gs.Dataset import Dataset

from xarray import register_dataset_accessor

@register_dataset_accessor("gs_tabular")
class Tabular(Dataset):
    """Accessor to xarray.Dataset that handles Tabular data

    See Also
    --------
    gspy.Spatial_ref : For Spatial reference instantiation.

    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def _allowed_file_types(self):
        return ('aseg', 'csv', 'netcdf')

    @staticmethod
    def count_column_headers(columns):
        """Takes the header of a csv and counts repeated entries

        A header "depth[0], depth[1], depth[2] will create an entry {'depth':3}

        Parameters
        ----------
        columns : list of str
            list of column names

        Returns
        -------
        dict
            Dictionary with each unique column name and its count

        """
        out = {}
        for col in columns:
            if '[' in col:
                col = col.split('[')[0]
            if col in out:
                out[col] += 1
            else:
                out[col] = 1
        return out

    @property
    def is_netcdf(self):
        return self.type == 'netcdf'

    @property
    def type(self):
        """File type of the Tabular class

        Returns
        -------
        str
            File type
        """
        return self._type

    @type.setter
    def type(self, value):
        assert value in self._allowed_file_types, ValueError('type must be in {}'.format(self._allowed_file_types))
        self._type = value

    @classmethod
    def read(cls, filename, metadata_file=None, spatial_ref=None, **kwargs):
        """Instantiate a Tabular class from tabular data

        When reading the metadata and data file, the following are established in order
        * User defined dimensions
        * User defined coordinates
        * Columns are read in and/or combined and added to the Dataset as variables

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
        ..survey.Spatial_ref : For information on creating a spatial ref

        """

        tmp = xr.Dataset(attrs={})
        self = cls(tmp)

        self = self.set_spatial_ref(spatial_ref)

        # Read the GSPy json file.
        json_md = self.read_metadata(metadata_file)

        # Read in the data using the respective file type handler
        file = self.file_handler.read(filename, **kwargs)

        # Add the index coordinate
        self.add_coordinate_from_values('index',
                                         arange(file.nrecords, dtype=int32),
                                         discrete = True,
                                         is_dimension=True,
                                         **{'standard_name' : 'index',
                                            'long_name'     : 'Index of individual data points',
                                            'units'         : 'not_defined',
                                            'null_value'    : 'not_defined'})

        # Add the user defined coordinates-dimensions from the json file
        dimensions = json_md['dimensions']
        coordinates = json_md['coordinates']
        reverse_coordinates = {v:k for k,v in coordinates.items()}

        for key in list(dimensions.keys()):
            b = reverse_coordinates.get(key, key)
            # assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
            if isinstance(dimensions[key], dict):
                # dicts are defined explicitly in the json file.
                self = self.add_coordinate_from_dict(b, is_dimension=True, **dimensions[key])

        # Write out a template json file when no variable metadata is found
        if not 'variable_metadata' in json_md:
            cls._create_variable_metadata_template(metadata_file, file.df.columns, **json_md)

        # Add in the spatio-temporal coordinates
        for key in list(coordinates.keys()):
            coord = coordinates[key].strip()
            discrete = key in ('x', 'y', 'z', 't')

            dic = self.get_attrs(file, coord, **json_md['variable_metadata'].get(coord, {}))

            # Might need to handle already added coords from the dimensions dict.
            self.add_coordinate_from_values(key,
                                            file.df[coord].values,
                                            dimensions=["index"],
                                            discrete = discrete,
                                            is_projected = self.is_projected,
                                            is_dimension=False,
                                            **dic)

        column_counts = cls.count_column_headers(file.columns)

        # Combine the column headers in the file with keys from the json metadata
        # If there is a variable with raw columns specified, we need to remove those individual columns
        # Otherwise they are duplicated.
        for key, item in json_md['variable_metadata'].items():
            if key not in column_counts:
                if 'raw_data_columns' in item:
                    for raw_key in item['raw_data_columns']:
                        del column_counts[raw_key]
                column_counts[key] = 'None'

        # Now we have all dimensions and coordinates defined.
        # Start adding the data variables
        for var in column_counts:

            var_meta = self.get_attrs(file, var, **json_md['variable_metadata'].get(var, {}))

            if not var in coordinates.keys():
                all_columns = sorted(list(file.df.columns))

                # Use a column from the CSV file and add it as a variable
                if var in all_columns:
                    self = self.add_variable_from_values(var,
                                                  file.df[var].values,
                                                  dimensions = ["index"],
                                                  **var_meta)

                else: # The CSV column header is a 2D variable with [x] in the column name
                    values = None
                    # check for raw_data_columns to combine
                    if 'raw_data_columns' in var_meta:
                        values = file.df[var_meta['raw_data_columns']].values

                    # if variable has multiple columns with [i] increment, to be combined
                    elif (var in column_counts) and (column_counts[var] > 1):
                        values = file.df[["{}[{}]".format(var, i) for i in range(column_counts[var])]].values

                    assert values is not None, ValueError(('{} not in data file, double check, '
                                                          'raw_data_columns field required in variable_metadata '
                                                          'if needing to combine unique columns to new variable without an [i] increment').format(var))

                    assert 'dimensions' in var_meta, ValueError('No dimensions found for 2+ dimensional variable {}.  Please add "dimensions":[---, ---]'.format(var))
                    assert all([dim in self._obj.dims for dim in var_meta['dimensions']]), ValueError("Could not match variable dimensions {} with json dimensions {}".format(var_meta['dimensions'], self._obj.dims))

                    self.add_variable_from_values(var, values, **var_meta)

        # add global attrs to tabular, skip variable_metadata and dimensions
        self.update_attrs(**json_md['dataset_attrs'])

        return self._obj

    @classmethod
    def open_netcdf(cls, filename, group='tabular', **kwargs):
        """Lazy loads a netCDF file but enforces CF convention when opening

        Parameters
        ----------
        filename : str
            NetCDF file
        group : str, optional
            The NetCDF group containing Tabular data, by default 'tabular'

        Returns
        -------
        xarray.Dataset

        """
        return super(Tabular, cls).open_netcdf(filename, group, **kwargs)

    def get_fortran_format(self, key, default_f32='f10.3', default_f64='g16.6'):

        values = self._obj.data_vars[key]

        if 'format' in values.attrs:
            return values.attrs['format']

        dtype = values.dtype
        if dtype == np.int32:

            # Get the max required spaces
            large = np.max(np.abs(values))
            p1 = values.min() < 0.0

            out = "i{}".format(large%10 + p1)
        if dtype == np.float32:
            out = default_f32
        if dtype == np.float64:
            out = default_f64

        if values.ndim == 2:
            out = "{}".format(values.shape[1]) + out

        return out

    def write_netcdf(self, filename, group='tabular'):
        """Write to netcdf file

        Parameters
        ----------
        filename : str
            Path to the file
        group : str, optional
            Netcdf group name to use inside netcdf file. Default is 'tabular'

        """
        super().write_netcdf(filename, group)

    def write_zarr(self, filename, group='tabular'):
        """Write to netcdf file

        Parameters
        ----------
        filename : str
            Path to the file
        group : str, optional
            Netcdf group name to use inside netcdf file. Default is 'tabular'

        """
        super().write_zarr(filename, group)
