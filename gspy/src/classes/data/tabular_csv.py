import os
from copy import deepcopy
import json
from pprint import pprint

from numpy import arange, int32
import xarray as xr
import pandas as pd

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
    def file(self):
        return self._file

    @file.setter
    def file(self, value):
        assert isinstance(value, pd.DataFrame), TypeError("file must have type pd.DataFrame")
        self._file = value

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

        self = cls()

        # self.type = 'csv'
        # self.filename = filename

        self = self.set_spatial_ref(spatial_ref)

        # Convert to xarray format
        json_md, path = self.read_metadata(metadata_file)

        dimensions = json_md['dimensions']
        coordinates = json_md['coordinates']
        reverse_coordinates = {v:k for k,v in coordinates.items()}

        for key in list(dimensions.keys()):
            b = reverse_coordinates.get(key, key)
            assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
            if isinstance(dimensions[key], dict):
                # dicts are defined explicitly in the json file.
                self = self.add_coordinate_from_dict(b, **dimensions[key])

        # Read the csv file
        file = pd.read_csv(filename, na_values=['NaN'])
        weird = (file.applymap(type) != file.iloc[0].apply(type)).any(axis=0)
        for w in weird.keys():
            if weird[w]:
                file[w] = pd.to_numeric(file[w], errors='coerce')

        # Write out a template json file when no variable metadata is found
        if not 'variable_metadata' in json_md:
            # ??? Fix Me
            Tabular_csv._create_variable_metadata_template(filename, file.columns)

        # Add the index coordinate
        self = self.add_coordinate_from_values('index',
                                               arange(file.values.shape[0], dtype=int32),
                                               dimensions = ['index'],
                                               discrete = True,
                                               **{'standard_name' : 'index',
                                                  'long_name' : 'Index of individual data points',
                                                  'units' : 'not_defined',
                                                  'null_value' : 'not_defined'})

        for key in list(coordinates.keys()):
            discrete = key in ('x', 'y', 'z')
            # Might need to handle already added coords from the dimensions dict.
            self = self.add_coordinate_from_values(key,
                                                   file[coordinates[key]].values,
                                                   dimensions=["index"],
                                                   discrete = discrete,
                                                   is_projected = self.is_projected,
                                                   **json_md['variable_metadata'][coordinates[key]])

        # Now we have all dimensions and coordinates defined.
        # Start adding the data variables
        # finish with regular data variables
        for var, var_meta in json_md['variable_metadata'].items():
            if not var in coordinates.keys():
                all_columns = sorted(list(file.columns))

                # Use a column from the CSV file and add it as a variable
                if var in all_columns:
                    self.add_variable_from_values(var,
                                                  file[var].values,
                                                  dimensions = ["index"],
                                                  **var_meta)

                else: # The CSV column header is a 2D variable with [x] in the column name
                    column_counts = Tabular_csv.count_column_headers(file.columns)

                    values = None
                    # check for raw_data_columns to combine
                    if 'raw_data_columns' in var_meta:
                        values = file[var_meta['raw_data_columns']].values

                    # if variable has multiple columns with [i] increment, to be combined
                    elif (var in column_counts) and (column_counts[var] > 1):
                        values = file[["{}[{}]".format(var, i) for i in range(column_counts[var])]].values

                    assert values is not None, ValueError('{} not in data file, double check, ', \
                                                          'raw_data_columns field required in variable_metadata ', \
                                                          'if needing to combine unique columns to new variable without an [i] increment'.format(var))

                    assert all([dim in self.dims for dim in var_meta['dimensions']]), ValueError("Could not match variable dimensions {} with json dimensions {}".format(var_meta['dimensions'], self.dims))

                    self.add_variable_from_values(var, values, **var_meta)

        # self._combine_pandas_json_to_xarray()

        #self.xarray = xr.Dataset.from_dataframe(self.file)

        #self._add_variable_metadata_to_xarray(dic['variable_metadata'])

        #for var in self.xarray.variables:
        #    if var not in self.xarray.dims.keys():
        #        self.assign_variable_attrs(var)

        #self.spatial_ref.reconcile_with_xarray(self.xarray, self.key_mapping)


        # self.xarray.attrs.update({'key_mapping.{}'.format(key): self.key_mapping[key] for key in self.key_mapping.keys()})
        # self.xarray.attrs.update(self.json_metadata['dataset_attrs'])

        # # add global attrs to tabular, skip variable_metadata and dimensions
        # self._add_general_metadata_to_xarray({key: values for key, values in self.json_metadata.items() if key not in ['dataset_attrs','dimensions', 'variable_metadata']})

        return self

    # def _combine_pandas_json_to_xarray(self):
    #     """ Read CSV file and construct the xarray Dataset
    #     """
    #     # finish with regular data variables
    #     for var, var_meta in self.json_metadata['variable_metadata'].items():

    #         # if not coordinate variables
    #         if not var in coord_keys:

    #             # if json variable matches csv column name
    #             if var in self.column_names:
    #                 array = deepcopy(self.file[var].values)

    #                 if 'dtype' in var_meta:
    #                     array1 = array.astype(var_meta['dtype'])
    #                 else:
    #                     array1 = self.file[var].values

    #                 if var_meta['null_value'] != 'not_defined':
    #                     array = array[array != var_meta['null_value']]
    #                 var_meta['valid_range'] = [np.nanmin(array), np.nanmax(array)]

    #                 self.xarray[var] = xr.DataArray(array1,
    #                                 dims=["index"],
    #                                 attrs=var_meta)

    #             # else if json variable not in csv
    #             else:
    #                 # check for raw_data_columns to combine
    #                 if 'raw_data_columns' in var_meta.keys():
    #                     vals = self.file[var_meta['raw_data_columns']].values

    #                 # if variable has multiple columns with [i] increment, to be combined
    #                 elif var in self.cols.keys() and self.cols[var] > 1:
    #                     vals = self.file[["{}[{}]".format(var, i) for i in range(self.cols[var])]].values

    #                 else:
    #                     vals = None

    #                 assert vals is not None, ValueError('{} not in data file, double check, raw_data_columns field required in variable_metadata if needing to combine unique columns to new variable without an [i] increment'.format(var))

    #                 # get variable dimensions from json, renaming with "centers" tag if bounds are passed
    #                 vdims = []
    #                 for vdim in var_meta.pop('dimensions'):
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

    #                     self.xarray[var] = xr.DataArray(vals,
    #                             dims=vdims,
    #                             attrs=var_meta)

    #                     # add dim attrs back in
    #                     for vdim in vdims:
    #                         self.xarray[vdim].attrs.update(vdim_attrs[vdim])
    #                 else:
    #                     #warnings.warn("{} passed dimensions do not align with data, skipping".format(var))
    #                     print("{} passed dimensions do not align with data, skipping".format(var))




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

        out_filename = "variable_metadata_template__{}.json".format(filename.split(os.sep)[-1].split('.')[0])
        with open(out_filename, "w") as f:
            json.dump(tmp_dic, f, indent=4)

        s = ("\nVariable metadata values are not defined in the supplemental information file.\n"
                "Creating a template with filename {}\n"
                "Please fill out and add the dictionary to the supplemental information file.\n").format(out_filename)

        raise Exception(s)

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
