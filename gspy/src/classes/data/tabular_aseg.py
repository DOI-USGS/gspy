import warnings
from copy import deepcopy

from pprint import pprint
import fortranformat as ff

from numpy import arange, int32
import numpy as np
import xarray as xr
# from aseg_gdf2 import read as read_aseg_gdf2
from ...utilities.aseg_gdf_handler import aseg_gdf2_gs
from .Tabular import Tabular

@xr.register_dataset_accessor("tabular_aseg")

class Tabular_aseg(Tabular):
    """Class to handle ASEG files.

    ``Tabular('aseg', data_filename, metadata_file, spatial_ref, **kwargs)``

    See Also
    --------
    gspy.Tabular_aseg.read : Class method for reading file into class
    gspy.Tabular : Parent and generic interface.

    """

    @property
    def column_names(self):
        return self.file.column_names()

    @property
    def cols(self):

        out = {}
        for label in self.column_names:
            dic = self.file.get_field_definition(label)
            if dic is None:
                if '[0]' in label:
                    dic = self.file.get_field_definition(label.split('[')[0])
                    out[label.split('[')[0]] = dic['cols']
            else:
                out[label] = dic['cols']

        return out

    @staticmethod
    def get_attrs(file_handle, variable, **kwargs):
        """Retrieve attribute information from ASEG field definitions

        Handle aseg gdf read errors and overload entries with gspy metadata

        Parameters
        ----------
        file : aseg_gdf2 file handler
            File handler
        variable : str
            Name of variable

        Other Parameters
        ----------------

        Returns
        -------
        out : dict
            dictionary of attributes for current variable

        """
        # Check for a multicolumn variable, prevent repeat inquire
        multi_column = '[' in variable

        if multi_column:
            if not '[0]' in variable:
                return None
            variable = variable.split('[')[0]

        dic = file_handle.metadata[variable]

        converter = np.int32 if 'i' in dic['format'] else np.float64
        dtype = kwargs.get('dtype', converter)

        # aseg_gdf2 has bugs in their dfn parser.  Handle that.
        tmp = dic['units']
        null_value = 'not_defined'
        if tmp != '':
            if ':' in tmp:
                unit, null_value = tmp.split(':')
                null_value = ((np.zeros(1) + converter(null_value.split('=')[-1])).astype(dtype))[0]
            else:
                unit = tmp
                if 'null_value' in dic:
                    if dic['null_value'] != "not_defined":
                        null_value = converter(dic['null_value'])
        else:
            unit = 'not_defined'

        out = {'standard_name' : variable.lower(),
            'format' : dic['format'],
            'long_name' : dic['long_name'],
            'units' : unit,
            'null_value' : null_value
        }

        return out | kwargs

    @property
    def file_handler(self):
        return aseg_gdf2_gs


    # @classmethod
    # def read(cls, filename, metadata_file=None, spatial_ref=None, **kwargs):
    #     """Read an aseg file

    #     Parameters
    #     ----------
    #     filename : str
    #         ASEG filename to read from.
    #     metadata_file : str, optional
    #         Json file to pull variable metadata from, by default None
    #     spatial_ref : gspy.Spatial_ref, optional
    #         Spatial reference system, by default None

    #     Returns
    #     -------
    #     out : gspy.Tabular_aseg
    #         Tabular class with ASEG data.

    #     See Also
    #     --------
    #     gspy.Spatial_ref : For Spatial reference instantiation.

    #     """

    #     self = cls()

    #     self = self.set_spatial_ref(spatial_ref)

    #     json_md = self.read_metadata(metadata_file)

    #     # # Read the ASEG file
    #     # file = read_aseg_gdf2(filename)

    #     file = aseg_gdf2_gs.read(filename)

    #     # Add the index coordinate
    #     self = self.add_coordinate_from_values('index',
    #                                            arange(file.nrecords, dtype=int32),
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

    #     # Add in the spatio-temporal coordinates
    #     for key in list(coordinates.keys()):
    #         coord = coordinates[key].strip()

    #         discrete = key in ('x', 'y', 'z', 't')
    #         dic = self.get_attrs(file, coord, **json_md['variable_metadata'].get(coord, {}))

    #         # Might need to handle already added coords from the dimensions dict.
    #         self = self.add_coordinate_from_values(key,
    #                                                file.df[coord].values,
    #                                                dimensions=["index"],
    #                                                discrete = discrete,
    #                                                is_projected = self.is_projected,
    #                                                is_dimension=False,
    #                                                **dic)

    #     column_counts = Tabular_aseg.count_column_headers(file.columns)

    #     for var in column_counts:
    #         if not var in coordinates.keys():
    #             all_columns = sorted(list(file.df.columns))

    #             var_meta = self.get_attrs(file, var, **json_md['variable_metadata'].get(var, {}))

    #             # Use a column from the CSV file and add it as a variable
    #             if var in all_columns:
    #                 self.add_variable_from_values(var,
    #                                               file.df[var].values,
    #                                               dimensions = ["index"],
    #                                               **var_meta)

    #             else: # The CSV column header is a 2D variable with [x] in the column name
    #                 values = None
    #                 # check for raw_data_columns to combine
    #                 if 'raw_data_columns' in var_meta:
    #                     values = file.df[var_meta['raw_data_columns']].values

    #                 # if variable has multiple columns with [i] increment, to be combined
    #                 elif (var in column_counts) and (column_counts[var] > 1):
    #                     values = file.df[["{}[{}]".format(var, i) for i in range(column_counts[var])]].values

    #                 assert values is not None, ValueError(('{} not in data file, double check, '
    #                                                         'raw_data_columns field required in variable_metadata '
    #                                                         'if needing to combine unique columns to new variable without an [i] increment'.format(var)))

    #                 assert 'dimensions' in var_meta, ValueError('No dimensions found for 2+ dimensional variable {}.  Please add "dimensions":[---, ---]')
    #                 assert all([dim in self.dims for dim in var_meta['dimensions']]), ValueError("Could not match variable dimensions {} with json dimensions {}".format(var_meta['dimensions'], self.dims))

    #                 self.add_variable_from_values(var, values, **var_meta)

    #     # add global attrs to tabular, skip variable_metadata and dimensions
    #     self.update_attrs(**json_md['dataset_attrs'])

    #     return self

    # def read_metadata(self, filename):
    #     """Read a supplemental information file

    #     Parses the dictionaries from the supplemental information and adds them to the appropriate classes.

    #     Parameters
    #     ----------
    #     filename : str
    #         A dictionary formatted ascii text file

    #     """
    #     # reading the data from the file
    #     with open(filename) as f:
    #         s = f.read()

    #     dic = json.loads(s)

    #     assert 'key_mapping' in dic, ValueError('Need to define key_mapping for required keys {} in supplemental'.format(key_mapping.required_keys))

    #     self.key_mapping = key_mapping(dic.pop('key_mapping'))

    #     self.json_metadata = dic

    # def _combine_asegpandas_json_to_xarray(self):
    #     """ Read ASEG file and construct the xarray Dataset
    #     """
    #     self.xarray = xr.Dataset()
    #     xr.set_options(keep_attrs=True)

    #     df = self.file.df()
    #     # start with dimension variables
    #     for dim, dim_meta in self.json_metadata['dimensions'].items():

    #         # if dimension has bounds
    #         if "bounds" in dim_meta.keys():

    #             #assert len(dim_meta["bounds"])-len(dim_meta["centers"]) == 1, ValueError('size of dimension bounds must be +1 size of centers')

    #             cntkey = '{}_centers'.format(dim)
    #             bndkey = '{}_bnds'.format(dim)

    #             # if already correct size/dimensions
    #             if np.array(dim_meta["bounds"]).shape == (len(dim_meta["centers"]), 2):
    #                 bounds = np.array(dim_meta["bounds"])

    #             # if 1D with +1 element, reshape
    #             elif np.array(dim_meta["bounds"]).shape == (len(dim_meta["centers"])+1,):
    #                 bounds = np.array((dim_meta["bounds"][:-1], dim_meta["bounds"][1:])).transpose()

    #             # otherwise, needs correcting
    #             else:
    #                 assert bounds.shape == (len(dim_meta["centers"]),2), ValueError('size of dimension bounds must be 2D array size of centers, or +1 list size of centers that can be reshaped')



    #             self.xarray[bndkey] = xr.DataArray(bounds,
    #                     dims=[cntkey, 'nv'],
    #                     coords={cntkey: dim_meta["centers"], 'nv': np.array([0,1])},
    #                     attrs={'standard_name' : '{}_bnds'.format(dim_meta["standard_name"].lower()),
    #                                 'long_name' : '{} bounds'.format(dim_meta["long_name"]),
    #                                 'units' : dim_meta["units"],
    #                                 'null_value' : dim_meta["null_value"]})

    #             self.xarray[cntkey] = xr.DataArray(dim_meta["centers"],
    #                     dims=[cntkey],
    #                     coords={cntkey: dim_meta["centers"]},
    #                     attrs={'standard_name' : '{}_centers'.format(dim_meta["standard_name"].lower()),
    #                                 'long_name' : '{} centers'.format(dim_meta["long_name"]),
    #                                 'units' : dim_meta["units"],
    #                                 'null_value' : dim_meta["null_value"],
    #                                 'bounds' : bndkey})

    #         # if discrete dimension
    #         else:

    #             self.xarray[dim] = xr.DataArray(dim_meta["centers"],
    #                     dims=[dim],
    #                     attrs={'standard_name' : '{}'.format(dim_meta["standard_name"].lower()),
    #                                 'long_name' : '{}'.format(dim_meta["long_name"]),
    #                                 'units' : dim_meta["units"],
    #                                 'null_value' : dim_meta["null_value"]})

    #     # set up coordinate varables
    #     coord_keys = [self.key_mapping['x'], self.key_mapping['y']]

    #     coords = {  'x': xr.DataArray(df[coord_keys[0]].values,
    #                                 dims=["index"],
    #                                 #coords=['x', 'y', 'spatial_ref'],
    #                                 #attrs=self.json_metadata['variable_metadata'][coord_keys[0]]),
    #                                 attrs=self.get_attrs(coord_keys[0])),
    #                 'y': xr.DataArray(df[coord_keys[1]].values,
    #                                 dims=["index"],
    #                                 #coords=['x', 'y', 'spatial_ref'],
    #                                 #attrs=self.json_metadata['variable_metadata'][coord_keys[1]]),
    #                                 attrs=self.get_attrs(coord_keys[1])),
    #                 'spatial_ref': xr.DataArray(0.0, attrs=self.spatial_ref)
    #                 }

    #     # x data variable
    #     self.xarray[coord_keys[0].strip()] = xr.DataArray(df[coord_keys[0]].values,
    #                         dims=["index"],
    #                         coords=coords,
    #                         #attrs=self.json_metadata['variable_metadata'][coord_keys[0]])
    #                         attrs=self.get_attrs(coord_keys[0]))
    #     # y data variable
    #     self.xarray[coord_keys[1].strip()] = xr.DataArray(df[coord_keys[1]].values,
    #                         dims=["index"],
    #                         coords=coords,
    #                         #attrs=self.json_metadata['variable_metadata'][coord_keys[1]])
    #                         attrs=self.get_attrs(coord_keys[1]))

    #     # if '_CoordinateTransformType' in self.spatial_ref.keys():
    #     #     self.xarray['x'].attrs['standard_name'] = 'projection_x_coordinate'
    #     #     self.xarray['x'].attrs['_CoordinateAxisType'] = 'GeoX'
    #     #     self.xarray['y'].attrs['standard_name'] = 'projection_y_coordinate'
    #     #     self.xarray['y'].attrs['_CoordinateAxisType'] = 'GeoY'
    #     if self.xarray['spatial_ref'].attrs['grid_mapping_name'] != 'latitude_longitude':
    #         self.xarray['x'].attrs['standard_name'] = 'projection_x_coordinate'
    #         self.xarray['y'].attrs['standard_name'] = 'projection_y_coordinate'

    #     # if units are abbreviated need to spell it out otherwise isn't recognized by Arc
    #     if self.xarray['x'].attrs['units'] == 'm':
    #         self.xarray['x'].attrs['units'] = 'meters'
    #     if self.xarray['x'].attrs['units'] == 'm':
    #         self.xarray['x'].attrs['units'] = 'meters'

    #     # finish with regular data variables
    #     additional_metadata = self.json_metadata['variable_metadata']

    #     for var in self.cols.keys():
    #         var_meta = self.get_attrs(var)
    #         add_meta = additional_metadata.get(var, None)
    #         if add_meta is not None:
    #             for key in add_meta.keys():
    #                 var_meta[key] = add_meta[key]

    #         # if not coordinate variables
    #         if not var in coord_keys:

    #             # if variable matches aseg column exactly
    #             if var in self.column_names:
    #                 array = deepcopy(df[var].values)

    #                 if 'dtype' in var_meta:
    #                     array1 = array.astype(var_meta['dtype'])
    #                 else:
    #                     array1 = df[var].values

    #                 if var_meta['null_value'] != 'not_defined':
    #                     array = array[array != var_meta['null_value']]
    #                 var_meta['valid_range'] = [np.nanmin(array), np.nanmax(array)]

    #                 self.xarray[var.strip()] = xr.DataArray(array1,
    #                                 dims=["index"],
    #                                 attrs=var_meta)
    #             else:

    #         #         # check for raw_data_columns to combine
    #         #         if 'raw_data_columns' in var_meta.keys():
    #         #             vals = self.file[var_meta['raw_data_columns']].values

    #                 # if variable has multiple columns with [i] increment, to be combined

    #                 vals = df[["{}[{}]".format(var, i) for i in range(self.cols[var])]].values

    #                 if 'dtype' in var_meta:
    #                     vals = vals.astype(var_meta['dtype'])

    #                 assert vals is not None, ValueError('{} not in data file, double check, raw_data_columns field required in variable_metadata if needing to combine unique columns to new variable without an [i] increment'.format(var))

    #                 vdims_in = self.json_metadata['variable_metadata'][var]

    #                 assert 'dimensions' in vdims_in, ValueError('2D variable [{}] missing dimensions key in json metadata'.format(var))

    #                 # get variable dimensions from json, renaming with "centers" tag if bounds are passed
    #                 vdims = []
    #                 for vdim in vdims_in['dimensions']:
    #                     if vdim in self.json_metadata['dimensions'].keys():
    #                         if "bounds" in self.json_metadata['dimensions'][vdim]:
    #                             vdim = '{}_centers'.format(vdim)
    #                     vdims.append(vdim)

    #                 # make sure dimensions align with data shape
    #                 check_flag = False
    #                 if vals.shape != tuple([self.xarray[vdim].size for vdim in vdims]):

    #                     # try reversing dimensions from json
    #                     vdims = vdims[::-1]

    #                     # if dimensions still do not line up, raise error
    #                     if vals.shape == tuple([self.xarray[vdim].size for vdim in vdims]):
    #                         check_flag = True
    #                 else:
    #                     check_flag = True

    #                 #assert check_flag, ValueError('{} variable dimensions do not align with data'.format(var))

    #                 if check_flag:
    #                     # store dim attrs, to replace after they get dropped when adding variable
    #                     vdim_attrs = {vdim: self.xarray[vdim].attrs for vdim in vdims}

    #                     tmp = deepcopy(vals)
    #                     if var_meta['null_value'] != 'not_defined':
    #                         tmp = tmp[tmp != var_meta['null_value']]
    #                     var_meta['valid_range'] = [np.nanmin(tmp), np.nanmax(tmp)]

    #                     # add variable to xarray
    #                     self.xarray[var.strip()] = xr.DataArray(vals,
    #                             dims=vdims,
    #                             attrs=var_meta)

    #                     # add dim attrs back in
    #                     for vdim in vdims:
    #                         self.xarray[vdim].attrs.update(vdim_attrs[vdim])
    #                 else:
    #                     warnings.warn("{} passed dimensions do not align with data, skipping".format(var))


    #     if 'nv' in self.xarray.dims:
    #         self.xarray['nv'].attrs = {'standard_name': 'number_of_vertices',
    #           'long_name' : 'Number of vertices for bounding variables',
    #           'units' : 'not_defined',
    #           'null_value' : 'not_defined'}

    #     if 'index' in self.xarray.dims:
    #         self.xarray['index'] = self.xarray['index'].assign_coords(coords)
    #         self.xarray['index'].attrs = {'standard_name': 'index',
    #           'long_name' : 'Index of individual data points',
    #           'units' : 'not_defined',
    #           'null_value' : 'not_defined'}

    #     # combine raw columns to new variables, if any are passed
    #     for var, var_meta in self.json_metadata['variable_metadata'].items():
    #         if 'raw_data_columns' in var_meta:

    #             if 'dimensions' in var_meta:
    #                 vdims = var_meta['dimensions']
    #                 # make sure index is assigned as dimension
    #                 if 'index' not in vdims:
    #                     vdims.append('index')
    #                 vdim = [dim for dim in vdims if dim != 'index'][0]
    #             else:
    #                 vdims = ["unnamed", "index"]

    #             # store dim attrs, to replace after they get dropped when adding variable
    #             if vdim != 'unnamed':
    #                 vdim_attrs = {vdim: self.xarray[vdim].attrs for vdim in vdims}

    #             if 'dtype' in var_meta:
    #                 array = xr.concat([self.xarray[val].astype(var_meta['dtype']) for val in var_meta['raw_data_columns']],
    #                                                               dim=vdim)
    #             else:
    #                 array = xr.concat([self.xarray[val] for val in var_meta['raw_data_columns']],
    #                                                               dim=vdim)

    #             self.xarray[var.strip()] = xr.DataArray(array,
    #                                             dims=vdims)

    #             # drop
    #             self._xarray = self.xarray.drop_vars(var_meta['raw_data_columns'])

    #             # add dimension attributes back in
    #             if vdim != 'unnamed':
    #                 self.xarray[vdim].attrs.update(vdim_attrs[vdim])

    #     # update variable metadata from json
    #     for var, var_meta in self.json_metadata['variable_metadata'].items():
    #         var_meta.pop('dimensions', None)
    #         if len(var_meta) > 0:
    #             self.xarray[var.strip()].attrs.update(var_meta)

    def write_aseg(self, filename):
        """Export tabular data to an ASEG formatted data file

        Parameters
        ----------
        filename : str
            Path to output aseg file

        """
        raise NotImplementedError("Cannot yet write to aseg")
