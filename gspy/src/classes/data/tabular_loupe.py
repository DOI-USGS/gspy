
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
        dic = file_handle.metadata[variable]

        out = {'standard_name' : dic['standard_name'],
            'long_name' : dic['long_name'],
            'units' : 'not_defined',
            'null_value' : "not_defined"
        }

        return out | kwargs