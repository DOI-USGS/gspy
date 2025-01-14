import os
import json
import matplotlib.pyplot as plt
from pprint import pprint

import xarray as xr
import numpy as np
from numpy import arange, int32

from .xarray_gs.Dataset import Dataset
from ..file_handlers import file_handler

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
        return self.file.type

    @type.setter
    def type(self, value):
        assert value in self._allowed_file_types, ValueError('type must be in {}'.format(self._allowed_file_types))
        self._type = value

    @staticmethod
    def metadata_template(filename,  metadata_file=None, system=None, **kwargs):

        tmp = xr.Dataset(attrs={})
        self = Tabular(tmp)

        self.file_handler = file_handler(filename)

        # Read the GSPy json file.
        json_md = {}
        if metadata_file is not None:
            if isinstance(metadata_file, str):
                json_md = self.read_metadata(metadata_file)
            else:
                json_md = metadata_file

        # Read in the data using the respective file type handler
        file = self.file_handler.read(filename, metadata=json_md.get('variables', {}))

        out = file.metadata_template

        if 'coordinates' in json_md:
            for k, v in json_md['coordinates'].items():
                out['variables'][v]['axis'] = k

        return out

    @classmethod
    def read(cls, filename, metadata_file=None, spatial_ref=None, system=None, **kwargs):
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

        self.file_handler = file_handler(filename)

        # Set the spatial ref
        self = self.set_spatial_ref(spatial_ref)

        # Read the GSPy json file.
        if isinstance(metadata_file, str):
            json_md = self.read_metadata(metadata_file)
        else:
            json_md = metadata_file

        # Read in the data using the respective file type handler
        file = self.file_handler.read(filename, metadata=json_md.get('variables', {}))

        # Add the index coordinate
        self.add_coordinate_from_values('index',
                                         values=arange(file.nrecords, dtype=int32),
                                         discrete = True,
                                         is_dimension=True,
                                         **{'standard_name' : 'index',
                                            'long_name'     : 'Index of individual data points',
                                            'units'         : 'not_defined',
                                            'null_value'    : 'not_defined'})

        # Add the user defined coordinates-dimensions from the json file
        dimensions = json_md.pop('dimensions', None)
        coordinates = json_md.pop('coordinates', None)

        if coordinates is not None:
            if dimensions is not None:
                for key in list(dimensions.keys()):
                    b = coordinates.get(key, key)
                    # assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
                    if isinstance(dimensions[key], dict):
                        # dicts are defined explicitly in the json file.
                        self = self.add_coordinate_from_dict(b.lower(), is_dimension=True, **dimensions[key])

        # Write out a template json file when no variable metadata is found
        if not 'variables' in json_md:
            file.write_metadata_template()

        # Add in the spatio-temporal coordinates
        for key in list(coordinates.keys()):
            coord = coordinates[key].strip()
            discrete = key in ('x', 'y', 'z', 't')

            # Might need to handle already added coords from the dimensions dict.
            self.add_coordinate_from_values(key.lower(),
                                            values=file.df[coord].values,
                                            dimensions=["index"],
                                            discrete = discrete,
                                            is_projected = self.is_projected,
                                            is_dimension=False,
                                            **file.metadata[coord])

        column_counts = file.column_header_counts

        # Combine the column headers in the file with keys from the json metadata
        # If there is a variable with raw columns specified, we need to remove those individual columns
        # Otherwise they are duplicated.
        for key, item in file.metadata.items():
            if key not in column_counts:
                if 'raw_data_columns' in item:
                    for raw_key in item['raw_data_columns']:
                        del column_counts[raw_key]
                column_counts[key] = 'None'

        # Now we have all dimensions and coordinates defined.
        # Start adding the data variables
        for var in column_counts:

            var_meta = file.metadata[var]

            if not var in coordinates.keys():
                all_columns = sorted(list(file.df.columns))

                # Use a column from the CSV file and add it as a variable
                if var in all_columns:
                    self = self.add_variable_from_values(var.lower(),
                                                  values=file.df[var].values,
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
                                                          'raw_data_columns field required in variables '
                                                          'if combining unique columns to a new variable without an [i] increment').format(var))

                    assert 'dimensions' in var_meta, ValueError('No dimensions found for 2+ dimensional variable {}.  Please add "dimensions":[---, ---]'.format(var))
                    # Check for the dimensions of the variable and try adding from a system class.

                    for dim in var_meta['dimensions']:
                        if dim.lower() not in self._obj.dims:
                            if system is not None:
                                for key, item in system.items():
                                    if dim.lower() in item.coords:
                                        self._obj = self._obj.assign_coords({dim.lower():item.coords[dim.lower()]})

                    assert all([dim.lower() in self._obj.dims for dim in var_meta['dimensions']]), ValueError("Could not match variable dimensions {} with json dimensions {}".format(var_meta['dimensions'], self._obj.dims))

                    self.add_variable_from_values(var, values=values, **var_meta)

        # add global attrs to tabular, skip variables and dimensions
        self.update_attrs(**json_md['dataset_attrs'])

        return self._obj

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

    def interpolate(self, dx, dy, variable, **kwargs):
        from geobipy import Point

        pc3d = Point(self['x'], self['y'], None)
        pc3d.interpolate()


    def plot_cross_section(self, line_number, variable, hang_from='elevation', **kwargs):

        keys = ['line', variable, 'layer_depth_bnds']

        if hang_from is not None:
            keys.append(hang_from)

        subset = self._obj[keys]
        subset = subset.where(subset.line == line_number, drop=True)

        from geobipy import StatArray, RectilinearMesh2D, Model

        x = subset.gs_tabular.x_axis(kwargs.pop('axis', 'x'))

        z = subset['layer_depth_bnds'].values
        z = np.hstack([z[:, 0, 0], z[-1, -1, 0]])

        if hang_from is not None:
            hanger = subset[hang_from]
            mesh = RectilinearMesh2D(x_centres = StatArray(x.values, name=x.attrs['standard_name'], units=x.attrs['units']),
                                    y_edges = StatArray(-z, name=subset['layer_depth'].attrs['standard_name'], units=subset['layer_depth'].attrs['units']),
                                    y_relative_to = StatArray(hanger.values, name=hanger.attrs['standard_name'], units=hanger.attrs['units']))
        else:
            mesh = RectilinearMesh2D(x_centres = StatArray(x.values, name=x.attrs['standard_name'], units=x.attrs['units']),
                                     y_edges = StatArray(-z, name=subset['layer_depth'].attrs['standard_name'], units=subset['layer_depth'].attrs['units']))

        v = subset[variable]
        model = Model(mesh = mesh, values=StatArray(v.values, name=v.attrs['standard_name'], units=v.attrs['units']))

        return model.pcolor(**kwargs)

    @property
    def distance_along_line(self):
        # Check the crs
        if self.is_projected:
            out = np.sqrt((self._obj['x'] - self._obj['x'][0])**2.0 + (self._obj['y'] - self._obj['y'][0])**2.0)
            out.attrs['standard_name'] = 'Distance'
            out.attrs['units'] = self._obj['x'].attrs['units']
            return out

        else:
            # Haversine
            from ...utilities.maths import haversine_distance
            out = haversine_distance(self._obj['x'], self._obj['y'], self._obj['x'][0], self._obj['y'][0])
            out.attrs['standard_name'] = 'Distance'
            out.attrs['units'] = 'm'
            return out

    def x_axis(self, axis):

        if axis in ['x', 'y']:
            return self._obj[axis]
        elif axis == 'distance':
            return self.distance_along_line


        assert False, ValueError("axis must be in ['x', 'y', 'distance']")

    def to_file(self, filename, **kwargs):

        file_handler = file_handler(filename)

        file_handler.to_file(self._obj, filename, **kwargs)