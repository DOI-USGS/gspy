import os
from copy import deepcopy
import json

import numpy as np
import xarray as xr
import pandas as pd

from .Tabular import Tabular
from .Variable_Metadata import variable_metadata

class Tabular_csv(Tabular):
    """Class to handle tabular csv files.

    ``Tabular('csv', data_filename, metadata_file, spatial_ref, **kwargs)``

    See Also
    --------
    gspy.Tabular_csv.read : Class method for reading file into class
    gspy.Tabular : Parent and generic interface.

    """

    @property
    def column_names(self):
        tmp_cols = list(self.file.columns)
        tmp_cols.sort()
        return tmp_cols

    @property
    def cols(self):
        out = {}
        n_cols = np.size(self.column_names)
        for i in range(n_cols):

            if '[0]' in self.column_names[i]:
                j = 1
                label = self.column_names[i].split('[')[0]
                while label == self.column_names[i+j].split('[')[0]:
                    j += 1
                    if i+j == n_cols:
                        break
                out[label] = j
                i += j
            elif not '[' in self.column_names[i]:
                out[self.column_names[i]] = 1

        return out

    @property
    def file(self):
        return self._file

    @file.setter
    def file(self, value):
        assert isinstance(value, pd.DataFrame), TypeError("file must have type pd.DataFrame")
        self._file = value

    def get_attrs(self, variable):
        """Create attribute information for data from a CSV file

        Parameters
        ----------
        variable : str
            Name of variable

        Returns
        -------
        out : dict
            dictionary of attributes for current variable

        """

        # Set up Defaults
        # out = {'standard_name' : variable,
        #     'format' : self.file._metadata[variable],
        #     'long_name' : variable,
        #     'units' : "not_defined",
        #     'null_value' : "not_defined"
        # }

        # format
        vtype = str(self.xarray[variable].dtype)
        tmpvals = deepcopy(self.xarray[variable].values.flatten())
        if 'int' in vtype or 'float' in vtype:
            if 'null_value' in self.xarray[variable].attrs.keys():
                nval = self.xarray[variable].attrs['null_value']
            else:
                nval = 'not_defined'
            if nval != 'not_defined':
                tmpvals[tmpvals == nval] = np.nan
        if 'int' in vtype:
            vformat = 'i{}'.format(len(str(np.nanmax(np.abs(tmpvals))))+1)
        elif 'float' in vtype:
            maxval = str(np.nanmax(np.abs(tmpvals)))
            if 'e' in maxval:
                vtype2 = 'e'
                maxval = maxval.split('e')[0]
            else:
                vtype2 = 'f'
            pad = 1 if np.nanmin(tmpvals) >= 0.0 else 2

            vformat = '{}{}.{}'.format(vtype2, len(maxval)+pad, len(maxval.split('.')[1]))
        else:
            vformat = 'not_defined'

        if len(self.xarray[variable].shape) == 2:
            vformat = '{}{}'.format(self.xarray[variable].shape[0], vformat)

        # default
        out = {'standard_name' : variable,
            'format' : vformat,
            'long_name' : variable,
            'units' : "not_defined",
            'null_value' : "not_defined"
        }
        # Update missing attributes
        out = {key: out[key] for key in out.keys() if not key in self.xarray[variable].attrs}

        return out

    @classmethod
    def read(cls, filename, metadata_file=None, spatial_ref=None, **kwargs):
        """Read a csv file

        Parameters
        ----------
        filename : str
            Csv filename to read from.
        metadata_file : str, optional
            Json file to pull variable metadata from, by default None
        spatial_ref : gspy.Spatial_ref, optional
            Spatial reference system, by default None

        Returns
        -------
        out : gspy.Tabular
            Tabular class with csv data.

        See Also
        --------
        gspy.Spatial_ref : For Spatial reference instantiation.

        """

        self = cls(None, None, None)

        self.type = 'csv'
        self.filename = filename

        self.spatial_ref = kwargs if spatial_ref is None else spatial_ref

        # Read the csv file
        self.file = pd.read_csv(filename, na_values=['NaN'])

        weird = (self.file.applymap(type) != self.file.iloc[0].apply(type)).any(axis=0)
        for w in weird.keys():
            if weird[w]:
                self.file[w] = pd.to_numeric(self.file[w], errors='coerce')

        # Convert to xarray format
        self.read_metadata(metadata_file)

        if not 'variable_metadata' in self.json_metadata.keys():
            self.create_variable_metadata_template(filename)

        self._combine_pandas_json_to_xarray()

        #self.xarray = xr.Dataset.from_dataframe(self.file)

        #self._add_variable_metadata_to_xarray(dic['variable_metadata'])

        #for var in self.xarray.variables:
        #    if var not in self.xarray.dims.keys():
        #        self.assign_variable_attrs(var)

        #self.spatial_ref.reconcile_with_xarray(self.xarray, self.key_mapping)

        # update 2D variables
        #self.update_dimensions(dic.pop("variable_metadata"))

        self.xarray.attrs.update({'key_mapping.{}'.format(key): self.key_mapping[key] for key in self.key_mapping.keys()})
        self.xarray.attrs.update(self.json_metadata['dataset_attrs'])

        # add global attrs to tabular, skip variable_metadata and dimensions
        self._add_general_metadata_to_xarray({key: values for key, values in self.json_metadata.items() if key not in ['dataset_attrs','dimensions', 'variable_metadata']})

        return self

    def _combine_pandas_json_to_xarray(self):
        """ Read CSV file and construct the xarray Dataset
        """

        self.xarray = xr.Dataset()
        xr.set_options(keep_attrs=True)

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
                        coords={cntkey: dim_meta["centers"], 'nv': np.array([0, 1])},
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
        coords = {  'x': xr.DataArray(self.file[coord_keys[0]].values,
                                    dims=["index"],
                                    #coords=['x', 'y', 'spatial_ref'],
                                    attrs=self.json_metadata['variable_metadata'][coord_keys[0]]),
                    'y': xr.DataArray(self.file[coord_keys[1]].values,
                                    dims=["index"],
                                    #coords=['x', 'y', 'spatial_ref'],
                                    attrs=self.json_metadata['variable_metadata'][coord_keys[1]]),
                    'spatial_ref': xr.DataArray(0.0, attrs=self.spatial_ref)
                    }
        # x data variable
        self.xarray[coord_keys[0]] = xr.DataArray(self.file[coord_keys[0]].values,
                            dims=["index"],
                            coords=coords,
                            attrs=self.json_metadata['variable_metadata'][coord_keys[0]])
        # y data variable
        self.xarray[coord_keys[1]] = xr.DataArray(self.file[coord_keys[1]].values,
                            dims=["index"],
                            coords=coords,
                            attrs=self.json_metadata['variable_metadata'][coord_keys[1]])

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
        for var, var_meta in self.json_metadata['variable_metadata'].items():

            # if not coordinate variables
            if not var in coord_keys:

                # if json variable matches csv column name
                if var in self.column_names:
                    array = deepcopy(self.file[var].values)

                    if 'dtype' in var_meta:
                        array1 = array.astype(var_meta['dtype'])
                    else:
                        array1 = self.file[var].values

                    if var_meta['null_value'] != 'not_defined':
                        array = array[array != var_meta['null_value']]
                    var_meta['valid_range'] = [np.nanmin(array), np.nanmax(array)]

                    self.xarray[var] = xr.DataArray(array1,
                                    dims=["index"],
                                    attrs=var_meta)

                # else if json variable not in csv
                else:
                    # check for raw_data_columns to combine
                    if 'raw_data_columns' in var_meta.keys():
                        vals = self.file[var_meta['raw_data_columns']].values

                    # if variable has multiple columns with [i] increment, to be combined
                    elif var in self.cols.keys() and self.cols[var] > 1:
                        vals = self.file[["{}[{}]".format(var, i) for i in range(self.cols[var])]].values

                    else:
                        vals = None

                    assert vals is not None, ValueError('{} not in data file, double check, raw_data_columns field required in variable_metadata if needing to combine unique columns to new variable without an [i] increment'.format(var))

                    # get variable dimensions from json, renaming with "centers" tag if bounds are passed
                    vdims = []
                    for vdim in var_meta.pop('dimensions'):
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

                        self.xarray[var] = xr.DataArray(vals,
                                dims=vdims,
                                attrs=var_meta)

                        # add dim attrs back in
                        for vdim in vdims:
                            self.xarray[vdim].attrs.update(vdim_attrs[vdim])
                    else:
                        #warnings.warn("{} passed dimensions do not align with data, skipping".format(var))
                        print("{} passed dimensions do not align with data, skipping".format(var))

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

    def create_variable_metadata_template(self, filename):
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

        for var in self.column_names:
            tmp_dic['variable_metadata'][var] = {"standard_name": "not_defined", "long_name": "not_defined", "units": "not_defined", "null_value": "not_defined"}

        out_filename = "variable_metadata_template__{}.json".format(filename.split(os.sep)[-1].split('.')[0])
        with open(out_filename, "w") as f:
            json.dump(tmp_dic, f, indent=4)

        s = ("\nVariable metadata values are not defined in the supplemental information file.\n"
                "Creating a template with filename {}\n"
                "Please fill out and add the dictionary to the supplemental information file.\n").format(out_filename)

        assert 'variable_metadata' in self.json_metadata, ValueError(s)

    def _add_variable_metadata_to_xarray(self, value):
        """Add Variable Metadata

        Updates the units and null_values for all variables based on dictionary in supplemental file

        Parameters
        ----------
        value : dict
            Attribute information on all variables, read from supplemental survey file

        """
        units = variable_metadata(**value)
        for var in self.xarray.variables:

            if '[' in var:
                var = var.split('[')[0]

            if var not in self.xarray.dims.keys():
                for key in units[var].keys():
                    self.xarray[var].attrs[key] = units[var][key]

    def write_csv(self, filename):
        """Export tabular_csv to CSV file

        Parameters
        ----------
        filename : str
            Path to output csv file

        """
        tmpdf = self.xr_to_dataframe()
        tmpdf.to_csv(filename, index=None)
