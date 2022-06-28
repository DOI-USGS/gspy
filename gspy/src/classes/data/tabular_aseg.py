import warnings
from copy import deepcopy

import numpy as np
import xarray as xr
import aseg_gdf2
from aseg_gdf2 import read as read_aseg_gdf2

from .Tabular import Tabular

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

    @property
    def file(self):
        return self._file

    @property
    def file_df(self):
        return self._file_df

    @file.setter
    def file(self, value):
        assert isinstance(value, aseg_gdf2.gdf2.GDF2), TypeError("file must have type aseg.GDF2")
        self._file = value

    def get_attrs(self, variable):
        """Retrieve attribute information from ASEG field definitions

        Parameters
        ----------
        variable : str
            Name of variable

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

        dic = self.file.get_field_definition(variable)

        tmp = dic['unit']
        if not tmp == '':
            if ':' in tmp:
                unit, null_value = tmp.split(':')
                null_value = np.float(null_value.split('=')[-1])
            else:
                unit = tmp
                null_value = np.float(dic['null']) if not dic['null'] is None else -9999999999.0
        else:
            unit = 'unknown'
            null_value = np.nan

        out = {'standard_name' : variable.lower(),
            'format' : dic['format'],
            'long_name' : dic['long_name'],
            'units' : unit,
            'null_value' : null_value
        }
        return out

    @classmethod
    def read(cls, filename, metadata_file=None, spatial_ref=None, **kwargs):
        """Read an aseg file

        Parameters
        ----------
        filename : str
            ASEG filename to read from.
        metadata_file : str, optional
            Json file to pull variable metadata from, by default None
        spatial_ref : gspy.Spatial_ref, optional
            Spatial reference system, by default None

        Returns
        -------
        out : gspy.Tabular_aseg
            Tabular class with ASEG data.

        See Also
        --------
        gspy.Spatial_ref : For Spatial reference instantiation.

        """

        self = cls(None, None, None)

        self.type = 'aseg'
        self.filename = filename

        # Read the ASEG file
        self.file = read_aseg_gdf2(filename)
        # self.file_df = self.file.df()
        # self.file_df.columns = [col.strip() for col in self.file_df.columns]

        self.spatial_ref = kwargs if spatial_ref is None else spatial_ref

        # Convert to xarray format
        # self.xarray = xr.Dataset.from_dataframe(self.file.df())

        # # Add attrs to xarray entries
        # for label in self.file.column_names():
        #     self.assign_variable_attrs(label)

        self.read_metadata(metadata_file)
        self._combine_asegpandas_json_to_xarray()

        #self.update_dimensions(dic.pop("variable_metadata"))

        # # add global attrs to linedata
        # self._add_general_metadata_to_xarray(dic)

        self.spatial_ref = kwargs if spatial_ref is None else spatial_ref

        self.xarray.attrs.update({'key_mapping.{}'.format(key): self.key_mapping[key] for key in self.key_mapping.keys()})
        self.xarray.attrs.update(self.json_metadata['dataset_attrs'])

        # add global attrs to tabular, skip variable_metadata and dimensions
        self._add_general_metadata_to_xarray({key: values for key, values in self.json_metadata.items() if key not in ['dataset_attrs','dimensions', 'variable_metadata']})

        return self

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

    def _combine_asegpandas_json_to_xarray(self):
        """ Read ASEG file and construct the xarray Dataset
        """
        self.xarray = xr.Dataset()
        xr.set_options(keep_attrs=True)

        df = self.file.df()
        # start with dimension variables
        for dim, dim_meta in self.json_metadata['dimensions'].items():

            # if dimension has bounds
            if "bounds" in dim_meta.keys():

                #assert len(dim_meta["bounds"])-len(dim_meta["centers"]) == 1, ValueError('size of dimension bounds must be +1 size of centers')

                cntkey = '{}_centers'.format(dim)
                bndkey = '{}_bnds'.format(dim)

                # if already correct size/dimensions
                if np.array(dim_meta["bounds"]).shape == (len(dim_meta["centers"]), 2):
                    bounds = np.array(dim_meta["bounds"])

                # if 1D with +1 element, reshape
                elif np.array(dim_meta["bounds"]).shape == (len(dim_meta["centers"])+1,):
                    bounds = np.array((dim_meta["bounds"][:-1], dim_meta["bounds"][1:])).transpose()

                # otherwise, needs correcting
                else:
                    assert bounds.shape == (len(dim_meta["centers"]),2), ValueError('size of dimension bounds must be 2D array size of centers, or +1 list size of centers that can be reshaped')



                self.xarray[bndkey] = xr.DataArray(bounds,
                        dims=[cntkey, 'nv'],
                        coords={cntkey: dim_meta["centers"], 'nv': np.array([0,1])},
                        attrs={'standard_name' : '{}_bnds'.format(dim_meta["standard_name"].lower()),
                                    'long_name' : '{} bounds'.format(dim_meta["long_name"]),
                                    'units' : dim_meta["units"],
                                    'null_value' : dim_meta["null_value"]})

                self.xarray[cntkey] = xr.DataArray(dim_meta["centers"],
                        dims=[cntkey],
                        coords={cntkey: dim_meta["centers"]},
                        attrs={'standard_name' : '{}_centers'.format(dim_meta["standard_name"].lower()),
                                    'long_name' : '{} centers'.format(dim_meta["long_name"]),
                                    'units' : dim_meta["units"],
                                    'null_value' : dim_meta["null_value"],
                                    'bounds' : bndkey})

            # if discrete dimension
            else:

                self.xarray[dim] = xr.DataArray(dim_meta["centers"],
                        dims=[dim],
                        attrs={'standard_name' : '{}'.format(dim_meta["standard_name"].lower()),
                                    'long_name' : '{}'.format(dim_meta["long_name"]),
                                    'units' : dim_meta["units"],
                                    'null_value' : dim_meta["null_value"]})

        # set up coordinate varables
        coord_keys = [self.key_mapping['x'], self.key_mapping['y']]

        coords = {  'x': xr.DataArray(df[coord_keys[0]].values,
                                    dims=["index"],
                                    #coords=['x', 'y', 'spatial_ref'],
                                    #attrs=self.json_metadata['variable_metadata'][coord_keys[0]]),
                                    attrs=self.get_attrs(coord_keys[0])),
                    'y': xr.DataArray(df[coord_keys[1]].values,
                                    dims=["index"],
                                    #coords=['x', 'y', 'spatial_ref'],
                                    #attrs=self.json_metadata['variable_metadata'][coord_keys[1]]),
                                    attrs=self.get_attrs(coord_keys[1])),
                    'spatial_ref': xr.DataArray(0.0, attrs=self.spatial_ref)
                    }

        # x data variable
        self.xarray[coord_keys[0].strip()] = xr.DataArray(df[coord_keys[0]].values,
                            dims=["index"],
                            coords=coords,
                            #attrs=self.json_metadata['variable_metadata'][coord_keys[0]])
                            attrs=self.get_attrs(coord_keys[0]))
        # y data variable
        self.xarray[coord_keys[1].strip()] = xr.DataArray(df[coord_keys[1]].values,
                            dims=["index"],
                            coords=coords,
                            #attrs=self.json_metadata['variable_metadata'][coord_keys[1]])
                            attrs=self.get_attrs(coord_keys[1]))

        if '_CoordinateTransformType' in self.spatial_ref.keys():
            self.xarray['x'].attrs['standard_name'] = 'projection_x_coordinate'
            self.xarray['x'].attrs['_CoordinateAxisType'] = 'GeoX'
            self.xarray['y'].attrs['standard_name'] = 'projection_y_coordinate'
            self.xarray['y'].attrs['_CoordinateAxisType'] = 'GeoY'

        # if units are abbreviated need to spell it out otherwise isn't recognized by Arc
        if self.xarray['x'].attrs['units'] == 'm':
            self.xarray['x'].attrs['units'] = 'meters'
        if self.xarray['x'].attrs['units'] == 'm':
            self.xarray['x'].attrs['units'] = 'meters'

        # finish with regular data variables
        #for var, var_meta in self.json_metadata['variable_metadata'].items():
        for var in self.cols.keys():
            var_meta = self.get_attrs(var)

            # if not coordinate variables
            if not var in coord_keys:

                # if variable matches aseg column exactly
                if var in self.column_names:
                    array = deepcopy(df[var].values)
                    if var_meta['null_value'] != 'not_defined':
                        array = array[array != var_meta['null_value']]
                    var_meta['valid_range'] = [np.nanmin(array), np.nanmax(array)]

                    self.xarray[var.strip()] = xr.DataArray(df[var].values,
                                    dims=["index"],
                                    attrs=var_meta)
                else:

            #         # check for raw_data_columns to combine
            #         if 'raw_data_columns' in var_meta.keys():
            #             vals = self.file[var_meta['raw_data_columns']].values

                    # if variable has multiple columns with [i] increment, to be combined

                    vals = df[["{}[{}]".format(var, i) for i in range(self.cols[var])]].values

                    assert vals is not None, ValueError('{} not in data file, double check, raw_data_columns field required in variable_metadata if needing to combine unique columns to new variable without an [i] increment'.format(var))

                    vdims_in = self.json_metadata['variable_metadata'][var]

                    assert 'dimensions' in vdims_in, ValueError('2D variable [{}] missing dimensions key in json metadata'.format(var))

                    # get variable dimensions from json, renaming with "centers" tag if bounds are passed
                    vdims = []
                    for vdim in vdims_in['dimensions']:
                        if vdim in self.json_metadata['dimensions'].keys():
                            if "bounds" in self.json_metadata['dimensions'][vdim]:
                                vdim = '{}_centers'.format(vdim)
                        vdims.append(vdim)

                    # make sure dimensions align with data shape
                    check_flag = False
                    if vals.shape != tuple([self.xarray[vdim].size for vdim in vdims]):

                        # try reversing dimensions from json
                        vdims = vdims[::-1]

                        # if dimensions still do not line up, raise error
                        if vals.shape == tuple([self.xarray[vdim].size for vdim in vdims]):
                            check_flag = True
                    else:
                        check_flag = True

                    #assert check_flag, ValueError('{} variable dimensions do not align with data'.format(var))

                    if check_flag:
                        # store dim attrs, to replace after they get dropped when adding variable
                        vdim_attrs = {vdim: self.xarray[vdim].attrs for vdim in vdims}

                        tmp = deepcopy(vals)
                        if var_meta['null_value'] != 'not_defined':
                            tmp = tmp[tmp != var_meta['null_value']]
                        var_meta['valid_range'] = [np.nanmin(tmp), np.nanmax(tmp)]

                        # add variable to xarray
                        self.xarray[var.strip()] = xr.DataArray(vals,
                                dims=vdims,
                                attrs=var_meta)

                        # add dim attrs back in
                        for vdim in vdims:
                            self.xarray[vdim].attrs.update(vdim_attrs[vdim])
                    else:
                        warnings.warn("{} passed dimensions do not align with data, skipping".format(var))


        if 'nv' in self.xarray.dims:
            self.xarray['nv'].attrs = {'standard_name': 'number_of_vertices',
              'long_name' : 'Number of vertices for bounding variables',
              'units' : 'not_defined',
              'null_value' : 'not_defined'}

        if 'index' in self.xarray.dims:
            self.xarray['index'] = self.xarray['index'].assign_coords(coords)
            self.xarray['index'].attrs = {'standard_name': 'index',
              'long_name' : 'Index of individual data points',
              'units' : 'not_defined',
              'null_value' : 'not_defined'}

        # combine raw columns to new variables, if any are passed
        for var, var_meta in self.json_metadata['variable_metadata'].items():
            if 'raw_data_columns' in var_meta:

                if 'dimensions' in var_meta:
                    vdims = var_meta['dimensions']
                    # make sure index is assigned as dimension
                    if 'index' not in vdims:
                        vdims.append('index')
                    vdim = [dim for dim in vdims if dim != 'index'][0]
                else:
                    vdims = ["unnamed", "index"]

                # store dim attrs, to replace after they get dropped when adding variable
                if vdim != 'unnamed':
                    vdim_attrs = {vdim: self.xarray[vdim].attrs for vdim in vdims}

                self.xarray[var.strip()] = xr.DataArray(xr.concat([self.xarray[val] for val in var_meta['raw_data_columns']],
                                                dim=vdim),
                                                dims=vdims)

                # drop
                self._xarray = self.xarray.drop_vars(var_meta['raw_data_columns'])

                # add dimension attributes back in
                if vdim != 'unnamed':
                    self.xarray[vdim].attrs.update(vdim_attrs[vdim])

        # update variable metadata from json
        for var, var_meta in self.json_metadata['variable_metadata'].items():
            var_meta.pop('dimensions', None)
            if len(var_meta) > 0:
                self.xarray[var.strip()].attrs.update(var_meta)

    def write_aseg(self, filename):
        """Export tabular data to an ASEG formatted data file

        Parameters
        ----------
        filename : str
            Path to output aseg file

        """
        raise NotImplementedError("Cannot yet write to aseg")
