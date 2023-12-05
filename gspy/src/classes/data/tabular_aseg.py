import numpy as np
import xarray as xr
from ...utilities.aseg_gdf_handler import aseg_gdf2_gs
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

    def write_aseg(self, filename):
        """Export tabular data to an ASEG formatted data file

        Parameters
        ----------
        filename : str
            Path to output aseg file

        """
        raise NotImplementedError("Cannot yet write to aseg")
