import os
import numpy as np
import xarray as xr
from ...utilities.aseg_gdf_handler import aseg_gdf2_gs
from ...utilities import dump_metadata_to_file
from .Tabular import Tabular

@xr.register_dataset_accessor("gs_tabular_aseg")
class Tabular_aseg(Tabular):
    """Accessor to xarray.Dataset that handles ASEG Tabular data

    ``Tabular_aseg.read(data_filename, metadata_file, spatial_ref, **kwargs)``

    Parameters
    ----------
    filename : str
        Filename to read from.
    metadata_file : str, optional
        Json file name, by default None
    spatial_ref : dict or gspy.Spatial_ref or xarray.DataArray, optional
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
    def column_names(self):
        """Get all the column name from the file

        Returns
        -------
        list of str

        """
        return self.file.column_names()

    @property
    def cols(self):
        """Get the columns of an ASEG file

        Returns
        -------
        dict

        """
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
    def file_handler(self):
        """Class to handle file IO

        Returns
        -------
        aseg_gdf2

        """
        return aseg_gdf2_gs

    @staticmethod
    def get_attrs(file_handle, variable, **kwargs):
        """Retrieve attribute information from ASEG field definitions

        Handle aseg gdf read errors and overload entries with gspy metadata.
        Metadata is read from the GDF file, but gspy json files take precedence and will overwrite the GDF information.

        Parameters
        ----------
        file : aseg_gdf2 file handler
            File handler
        variable : str
            Name of variable

        Other Parameters
        ----------------
        long_name : str, optional
            CF convention long name
        null_value : int or float, optional
            Number that represents unusable data. default is 'not_defined'
        standard_name : str, optional
            CF convention standard name
        units : str, optional
            units of the coordinate

        Returns
        -------
        out : dict
            dictionary of metadata for current variable

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

    def write_aseg_dfn_file(self, filename, default_f32="f10.3", default_f64="g12.6"):

        skip_these = [self._obj.coords[x].attrs['bounds'] for x in self._obj.dims if 'bounds' in self._obj.coords[x].attrs]

        row = 0
        with open(filename, 'w') as f:
            f.write("DEFN   ST=RECD,RT=COMM;RT:A4;COMMENTS:A80\n")
            for i, key in enumerate(self._obj.data_vars):

                if key in skip_these:
                    continue

                var = self._obj[key]
                attrs = var.attrs

                # Grab the null value
                null = ""
                if attrs['null_value'] != "not_defined":
                    null = "NULL={},".format(attrs['null_value'])
                # Grab the units
                units = ""
                if 'units' in attrs:
                    if attrs['units'] != "not_defined":
                        units = "UNITS={},".format(attrs['units'])
                    # Grab the format if present, otherwise use a default

                fformat = attrs.get('format', self.get_fortran_format(key, default_f32=default_f32, default_f64=default_f64))

                strng = "DEFN {} ST=RECD,RT=;{}:{}:{}{}NAME={}\n".format(row, var.attrs['standard_name'], fformat, null, units, attrs['long_name'])
                f.write(strng)

                row += 1
            f.write("DEFN {} ST=RECD,RT=;END DEFN\n".format(row))
        """Export tabular data to an ASEG formatted data file

        Parameters
        ----------
        filename : str
            Path to output aseg file

        """
        raise NotImplementedError("Cannot yet write to aseg")

    def write_metadata_template(self, filename="aseg_md.yml"):
        """Write metadata template for an ASEG dataset

        Creates a template metadata file needed for adding ASEG data.
        Most metadata is pulled from the aseg definition file,
        but we require extra attributes to honour the CF convention.
        Additional dictionaries can be optionally added to document more information or
        ancillary metadata relevant to the specific variables.

        Raises
        ------
        Exception
            Tells user to specify metadata file when instantiating

        """

        print("\nGenerating an empty metadata file template.\n")

        out = {}
        out["dataset_attrs"] = {
            "content": "<summary statement of what the dataset contains>",
            "comment": "<additional details or ancillary information>"
            }

        out["coordinates"] = {
            "x" : "lat",
            "y" : "lon",
            "z" : "depth"
            }

        out["variable_metadata"] = {}

        dump_metadata_to_file(out, filename)

    @staticmethod
    def _create_variable_metadata_template(filename, *args, **kwargs):
        """Generates a template metadata file for variables only.

        Assumes metadata has been provided for the dataset already, but creates extra entries for variables.

        """
        tmp_dic = {}
        coords = kwargs['coordinates']
        if 'x' in coords:
            tmp_dic[coords['x']] = {"axis" : "X"}
        if 'y' in coords:
            tmp_dic[coords['y']] = {"axis" : "Y"}
        if 'z' in coords:
            tmp_dic[coords['z']] = {"axis" : "Z",
                                    "positive" : "up or down?",
                                    "datum" : "not_defined"}
        if 't' in coords:
            tmp_dic[coords['t']] = {"axis" : "T",
                                    "datum" : "not_defined"}

        template_filename = "{}_variable_metadata_template.{}".format(*filename.split(os.sep)[-1].split('.'))

        dump_metadata_to_file({'variable_metadata':tmp_dic}, template_filename)

        s = ("\nGspy requires additional metadata on top of the ASEG standard in order to honour the CF convention.\n"
             "We are creating a template file called {} that you need to fill out.\n"
             "Once filled out, add that 'variable_metadata' dictionary to the metadata file\n").format(template_filename)

        raise Exception(s)