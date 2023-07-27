import os
import json
import matplotlib.pyplot as plt
from pprint import pprint

import xarray as xr
import numpy as np
from numpy import arange, int32

from .xarray_gs.Dataset import Dataset

import xarray as xr
@xr.register_dataset_accessor("gs_tabular")
class Tabular(Dataset):
    """Class to handle tabular data.

    ``Tabular(type, data_filename, metadata_file, spatial_ref, **kwargs)``

    Parameters
    ----------
    type : str
        One of ['csv', 'aseg', 'netcdf']
    filename : str
        Csv filename to read from.
    metadata_file : str, optional
        Json file to pull variable metadata from, by default None
    spatial_ref : gspy.Spatial_ref, optional
        Spatial reference system, by default None

    Returns
    -------
    out : gspy.Tabular
        Tabular class.

    See Also
    --------
    gspy.Spatial_ref : For Spatial reference instantiation.

    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    # def __init__(self, type, data_filename, metadata_file=None, spatial_ref=None, **kwargs):
    #     # self._type = None
    #     # self._key_mapping = None
    #     if type is None:
    #         return

    #     if data_filename is not None:
    #         self.read(type, data_filename, metadata_file=metadata_file, spatial_ref=spatial_ref, **kwargs)

    def print_something(self):
        print('I am a Tabular')

    @property
    def _allowed_file_types(self):
        return ('aseg', 'csv', 'netcdf')

    @staticmethod
    def count_column_headers(columns):
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

    # @property
    # def key_mapping(self):
    #     return self._key_mapping

    # @key_mapping.setter
    # def key_mapping(self, value):
    #     if value is None:

    #         print("\nGenerating an empty mapping file for {}.\n".format(self.data_filename))

    #         tmp = self.required_mapping
    #         with open('{}_key_mapping.txt'.format(self.data_filename), 'w') as f:
    #             json.dump(tmp, f, indent=4)

    #         # raise Exception("Must specify a mapping file.")

    #     else:
    #         self._key_mapping = key_mapping(value)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        assert value in self._allowed_file_types, ValueError('type must be in {}'.format(self._allowed_file_types))
        self._type = value

    @classmethod
    def read(cls, filename, metadata_file=None, spatial_ref=None, **kwargs):

        tmp = xr.Dataset(attrs={})
        self = cls(tmp)

        self = self.set_spatial_ref(spatial_ref)

        # Read the GSPy json file.
        json_md = self.read_metadata(metadata_file)

        file = self.file_handler.read(filename)

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
            assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
            if isinstance(dimensions[key], dict):
                # dicts are defined explicitly in the json file.
                self = self.add_coordinate_from_dict(b, is_dimension=True, **dimensions[key])

        # Write out a template json file when no variable metadata is found
        if not 'variable_metadata' in json_md:
            # ??? Fix Me for ASEG
            cls._create_variable_metadata_template(filename, file.df.columns)

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

                    assert 'dimensions' in var_meta, ValueError('No dimensions found for 2+ dimensional variable {}.  Please add "dimensions":[---, ---]')
                    assert all([dim in self._obj.dims for dim in var_meta['dimensions']]), ValueError("Could not match variable dimensions {} with json dimensions {}".format(var_meta['dimensions'], self._obj.dims))

                    self.add_variable_from_values(var, values, **var_meta)

        # add global attrs to tabular, skip variable_metadata and dimensions
        self.update_attrs(**json_md['dataset_attrs'])

        return self._obj

    @classmethod
    def read_netcdf(cls, filename, group='tabular', **kwargs):
        return super(Tabular, cls).read_netcdf(filename, group, **kwargs)

    # Methods
    #def _add_general_metadata_to_xarray(self, kwargs):
    #    kwargs = flatten(kwargs, '', {})
    #    self.attrs.update(kwargs)

    def assign_variable_attrs(self, variable):
        """Assign attributes for given variable name

        Update xarray attributes with variable metadata

        Parameters
        ----------
        variable : str
            Name of variable

        """
        dic = self.get_attrs(variable)
        if '[' in variable:
            variable = variable.split('[')[0]

        if not dic is None:
            for key in dic.keys():
                self[variable.strip()].attrs[key] = dic[key]

    def check_valid_range(self):

        import numpy as np
        lows = np.zeros(len(self.keys()))
        highs = np.zeros(len(self.keys()))
        for i, key in enumerate(self.keys()):
            lows[i], highs[i] = self[key].attrs['valid_range']

        return np.min(lows), np.max(highs)



    def create_variable_metadata_template(self, filename):
        """Generates a template metadata file.

        The generated file contains gspy required entries in a metadata files; standard_name, long_name, units, null_value.

        Parameters
        ----------
        filename : str
            Generate a template for this file.

        """
        tmp_dic = {'variable_metadata':{}}

        for var in self.variables:
            tmp_dic['variable_metadata'][var] = {"standard_name": "not_defined", "long_name": "not_defined", "units": "not_defined", "null_value": "not_defined"}

        out_filename = "variable_metadata_template__{}.json".format(filename.split(os.sep)[-1].split('.')[0])
        with open(out_filename, "w") as f:
            json.dump(tmp_dic, f, indent=4)

        s = ("\nVariable metadata values are not defined in the supplemental information file.\n"
                "Creating a template with filename {}\n"
                "Please fill out and add the dictionary to the supplemental information file.\n").format(out_filename)

        assert 'variable_metadata' in self.json_metadata, ValueError(s)

    # def __reconcile_xarray(self):
    #     """Clean up xarray variables

    #     Combine multi-channel variables into single variables
    #     and add spatial reference variable.

    #     """
    #     if self.is_netcdf:
    #         return

    #     for key, value in self.cols.items():

    #         if value > 1:

    #             # if not 'channel' in self:
    #             #     self =
    #             channel = 'channel_{}'.format(value)

    #             # create new
    #             #print(key, value)
    #             check = [self.get("{}[{}]".format(key, i)) for i in range(value)]
    #             #print(check)
    #             self[key] = xr.DataArray(xr.concat(check, dim=channel),
    #                                             dims = [channel, 'index'])
    #                                             #coords = {channel:np.arange(value),
    #                                             #		'index':self.index})
    #                                             # attrs = self[key+'[0]'].attrs)

    #             # Delete
    #             self._xarray = self.drop_vars([key+'[%i]' % i for i in range(value)])

    #     #strip out whitespace in variable names
    #     oldnames=[str(var) for var in self.variables]
    #     newnames=[name.strip().replace(' ', '_') for name in oldnames]
    #     self._xarray = self.rename({oldnames[i]: newnames[i] for i in range(len(newnames))})

    # def update_dimensions(self, variable_metadata):
    #     """Update the dimensions in the xarray object.

    #     Parameters
    #     ----------
    #     variable_metadata : dict
    #         Dictionary of variable metadata

    #     """

    #     dimensions = [variable_metadata[var]["dimensions"] for var in variable_metadata if "dimensions" in variable_metadata[var]]
    #     dimensions = np.unique([dimdim for dim in dimensions for dimdim in dim if dimdim != "index" ])

    #     for dim in dimensions:

    #         vars = [var for var in variable_metadata if "dimensions" in variable_metadata[var] and dim in variable_metadata[var]["dimensions"]]
    #         for var in vars:

    #             if "bounds" in variable_metadata[dim].keys():

    #                 assert len(variable_metadata[dim]["bounds"])-len(variable_metadata[dim]["centers"]) == 1, ValueError('size of dimension bounds must be +1 size of centers')

    #                 cntkey = '{}_centers'.format(dim)
    #                 bndkey = '{}_bnds'.format(dim)
    #                 bnds_attrs = {'standard_name' : '{}_bnds'.format(variable_metadata[dim]["standard_name"].lower()),
    #                                     'long_name' : '{} bounds'.format(variable_metadata[dim]["long_name"]),
    #                                     'units' : variable_metadata[dim]["units"],
    #                                     'null_value' : variable_metadata[dim]["null_value"]}
    #                 cntr_attrs = {'standard_name' : '{}_centers'.format(variable_metadata[dim]["standard_name"].lower()),
    #                                     'long_name' : '{} centers'.format(variable_metadata[dim]["long_name"]),
    #                                     'units' : variable_metadata[dim]["units"],
    #                                     'null_value' : variable_metadata[dim]["null_value"],
    #                                     'bounds' : bndkey}

    #                 if not cntkey in self.variables:

    #                     bounds = np.array((variable_metadata[dim]["bounds"][:-1], variable_metadata[dim]["bounds"][1:])).transpose()

    #                     self[bndkey] = xr.DataArray(bounds,
    #                             dims=[cntkey, 'nv'],
    #                             #coords={cntkey: dimensions[dim]["centers"], 'nv': np.array([0,1])},
    #                             attrs=bnds_attrs)

    #                     self[cntkey] = xr.DataArray(variable_metadata[dim]["centers"],
    #                             dims=[cntkey],
    #                             #coords={cntkey: dimensions[dim]["centers"]},
    #                             attrs=cntr_attrs)
    #             else:

    #                 cntkey = '{}'.format(dim)
    #                 cntr_attrs = {'standard_name' : '{}'.format(variable_metadata[dim]["standard_name"].lower()),
    #                                     'long_name' : '{}'.format(variable_metadata[dim]["long_name"]),
    #                                     'units' : variable_metadata[dim]["units"],
    #                                     'null_value' : variable_metadata[dim]["null_value"]}

    #                 if not cntkey in self.variables:
    #                     self[cntkey] = xr.DataArray(variable_metadata[dim]["centers"],
    #                             dims=[cntkey],
    #                             attrs=cntr_attrs)

    #             self[var] = self[var].swap_dims({
    #                 [dm for dm in self[var].dims if 'channel' in dm][0]: cntkey})

    #             # replace attrs which get erased when swap dims, needs a better fix!!!!!
    #             self[cntkey].attrs.update(cntr_attrs)
    #             if "bounds" in variable_metadata[dim].keys():
    #                 self[bndkey].attrs.update(bnds_attrs)

    #     if 'nv' in self.dims:
    #         self['nv'].attrs = {'standard_name': 'number_of_vertices',
    #           'long_name' : 'Number of vertices for bounding variables',
    #           'units' : 'not_defined',
    #           'null_value' : 'not_defined'}

    #     if 'index' in self.dims:
    #         self['index'].attrs = {'standard_name': 'index',
    #           'long_name' : 'Index of individual data points',
    #           'units' : 'not_defined',
    #           'null_value' : 'not_defined'}

    #     return

    # def set_spatial_ref(self):
    #     s = [self.key_mapping['easting'], self.key_mapping['northing']]

    #     x = self[self.key_mapping['easting']]
    #     y = self[self.key_mapping['northing']]
    #     if '_CoordinateTransformType' in self.spatial_ref:
    #         x.attrs['standard_name'] = 'projection_x_coordinate'
    #         x.attrs['_CoordinateAxisType'] = 'GeoX'
    #         y.attrs['standard_name'] = 'projection_y_coordinate'
    #         y.attrs['_CoordinateAxisType'] = 'GeoY'

    #     # if units are abbreviated need to spell it out otherwise isn't recognized by Arc
    #     if x.attrs['units'] == 'm':
    #         x.attrs['units'] = 'meters'
    #     if y.attrs['units'] == 'm':
    #         y.attrs['units'] = 'meters'

    #     xy = xr.DataArray(0.0, attrs=self.spatial_ref)

    #     coords = {'y': y, 'x': x, 'spatial_ref': xy}

    #     for var in self.data_vars:
    #         da = self[var]
    #         if not var in s:
    #             da = da.assign_coords(coords)
    #             da.attrs['grid_mapping'] = self.spatial_ref['grid_mapping_name']
    #         self[var] = da

    def subset(self, key, value):
        """Subset xarray where xarray[key] == value

        Parameters
        ----------
        key : str
            Key in xarray Dataset
        value : scalar
            Subset where entry equals value

        Returns
        -------
        out : gspy.Tabular

        """
        out = type(self)()

        out._xarray = self.where(self[key] == value)
        out._spatial_ref = self.spatial_ref
        out._key_mapping = self.key_mapping

        return out

    def _get_bounding_box(self):
        """ Get Bounding Box Coordinates

        Return the bounding box coordinates

        Raises
        ------
        NotImplementedError
            Planned for future releases, not currently implemented
        """
        raise NotImplementedError()

    def write_netcdf(self, filename, group='tabular'):
        """Write to netcdf file

        Parameters
        ----------
        filename : str
            Path to the file
        group : str
            Netcdf group name to use inside netcdf file.

        """
        super().write_netcdf(filename, group)

    # Plotting

    # def plot(self, variable, x='x', **kwargs):
    #     """Plot Tabular data against co-ordinate variables

    #     Parameters
    #     ----------
    #     variable : str
    #         key in xarray Dataset to plot
    #     x : str, optional
    #         x axis to plot key against, by default 'easting'

    #     Returns
    #     -------
    #     ax : matplotlib.Axes
    #         plotting axis
    #     pt : matplotlib.pyplot.plot.
    #         Handle from plotting

    #     """
    #     # assert x in self.key_mapping, ValueError('x must be in required mapping {}'.format(list(key_mapping.required_keys())))

    #     ax = kwargs.pop('ax', plt.gca())

    #     x = self[self[x]]
    #     y = self[variable]

    #     pt = plt.plot(x, y, **kwargs)
    #     plt.xlabel(x.attrs['long_name'])
    #     ylab = y.attrs['long_name']
    #     if len(ylab) > 10:
    #         ylab = ylab.replace(' ', '\n')
    #     plt.ylabel(ylab)

    #     return ax, pt
