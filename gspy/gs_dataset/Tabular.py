import re
import xarray as xr
import numpy as np
from numpy import arange, int32

from .Dataset import Dataset
from ..metadata.Metadata import Metadata
from ..file_handlers import InsufficientMetadataError, handler_for, open_datafile

class Tabular(Dataset):
    """Accessor to xarray.Dataset that handles Tabular data

    See Also
    --------
    gspy.Spatial_ref : For Spatial reference instantiation.

    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @staticmethod
    def metadata_template(data, metadata_file=None, system=None, file_type=None, **kwargs):
        """Metadata template for some tabular data.

        Parameters
        ----------
        data : str or pandas.DataFrame or gspy.file_handlers.file_handler
            The data to describe, as a filename, a table already read in, or a
            handler that has already read one.
        metadata_file : str or dict, optional
            Existing metadata, whether complete or partial. Its entries win over
            the template's placeholders.
        system : xarray.DataTree, optional
            Needed by formats whose columns are named after a system's channels.
        file_type : str, optional
            Name a format explicitly instead of detecting it, e.g. 'loupe'.

        Returns
        -------
        gspy.Metadata

        """
        json_md = Metadata.read(metadata_file)

        # Get a handler for the data, reading it only if it is a filename
        file = open_datafile(data, metadata=json_md, system=system, file_type=file_type)

        return Tabular._template_from_handler(file, json_md)

    @staticmethod
    def _template_from_handler(file, json_md):
        """Fold what a handler knows about its file into a tabular metadata template."""
        out = file.metadata_template(**json_md, **file.file_metadata)
        out['dataset_attrs']['structure'] = 'tabular'

        for k, v in json_md.get('coordinates', {}).items():
            entry = out['variables'][v]
            if k == 'z':
                entry["positive"] = entry.get('positive', "?? up or down ??")
            if k in ('z', 't'):
                entry["datum"] = entry.get("datum", "?? what is the datum ??")

        return out

    @staticmethod
    def _systems(system):
        """The systems to look in, however the system was passed.

        A system arrives here as a tree of them, a dict of them, a lone dataset, or as
        nothing at all. Nothing to look in gives nothing back, which the callers report
        as a missing system or an unmatched dimension rather than walking into an
        attribute error.

        """
        if system is None:
            return []

        if isinstance(system, dict):
            return list(system.values())

        if isinstance(system, xr.DataTree):
            return [node for node in system.subtree
                    if (node.attrs.get('type') or '').lower() == 'system']

        return [system]

    @staticmethod
    def _couplet_labels(system):
        """Every couplet label in a system, however the system was passed."""
        return [label for dataset in Tabular._systems(system) if 'couplet_label' in dataset
                for label in dataset['couplet_label'].values]

    @staticmethod
    def _system_coordinate(system, dimension):
        """The coordinate a system defines for one of its own dimensions, or None.

        Only a system the dimension actually belongs to can supply it, and the first
        one that does is the answer. A system attached to a dataset inherits that
        dataset's coordinates, so a magnetometer hanging off an AEM dataset can see its
        gate times too, and answering with those would hand back the channels of
        whatever the system was attached to instead of the ones asked for - which is
        what happens when a system is iselled down to the channels a processed dataset
        kept, and some other system is passed alongside it.

        """
        for dataset in Tabular._systems(system):
            if not isinstance(dataset, (xr.Dataset, xr.DataTree)):
                continue

            owned = dataset.to_dataset(inherit=False) if isinstance(dataset, xr.DataTree) else dataset
            if dimension in owned.dims and dimension in dataset.coords:
                return dataset[dimension]

        return None

    @classmethod
    def read(cls, data, metadata_file=None, spatial_ref=None, **kwargs):
        """Instantiate a Tabular class from tabular data

        When reading the metadata and data file, the following are established in order
        * User defined dimensions
        * User defined coordinates
        * Columns are read in and/or combined and added to the Dataset as variables

        Parameters
        ----------
        data : str or pandas.DataFrame or gspy.file_handlers.file_handler
            The data to ingest, as any of

            * a filename, read with whichever handler recognises it
            * a DataFrame already in memory, for data that needed work before
              GSPy saw it
            * a handler that has already read its file, so a second pass over a
              large file is not needed

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
        gspy.file_handlers.open_datafile : How each form of ``data`` is handled

        """
        def column_matches(pattern, cols):
            return [(c, int(pattern.match(c).group(1))) for c in cols if pattern.match(c)]

        tmp = xr.Dataset(attrs={})
        self = cls(tmp)

        # Set the spatial ref
        self._obj = self._obj.gs.set_spatial_ref(spatial_ref)

        # Read the GSPy metadata file.
        json_md = Metadata.read(metadata_file)

        # Get a handler for the data, reading it only if it is a filename
        file = open_datafile(data, metadata=json_md.get('variables', {}), **kwargs)
        file_metadata = file.file_metadata

        system = kwargs.get('system', None)

        if file_metadata is not None:
            for k, v in file_metadata.items():
                json_md[k] = json_md.get(k, {}) | v

            if 'dimensions' in file_metadata:
                if system is not None:
                    for key, values in file_metadata['dimensions'].items():
                        if isinstance(system, dict):
                            system = system.gs.add_coordinate_from_dict(key, discrete=True, is_dimension=True, **values)
                        else:
                            if isinstance(system, xr.DataTree):
                                for path, node in system.items():
                                    system["/"+path] = node.to_dataset().gs.add_coordinate_from_dict(key, discrete=True, is_dimension=True, **values)
                            else: # xr.Dataset
                                system = system.gs.add_coordinate_from_dict(key, discrete=True, is_dimension=True, **values)

        # Hand back a template when there is no variable metadata to work with.
        # Before the coordinates are popped below, so the template keeps them.
        if not 'variables' in json_md:
            # file.filename, not the argument: for a DataFrame there is no path,
            # and the handler carries a label to use in its place.
            raise InsufficientMetadataError(template=cls._template_from_handler(file, json_md),
                                            filename=file.filename,
                                            missing=file.missing_metadata(json_md))

        # Add the index coordinate
        self._obj = self.add_coordinate_from_values('index',
                                         values=arange(file.nrecords, dtype=int32),
                                         discrete = True,
                                         is_dimension=True,
                                         **{'standard_name' : 'index',
                                            'long_name'     : 'Index of individual data points',
                                            'units'         : 'not_defined',
                                            'missing_value'    : 'not_defined'})

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
                        self._obj = self.add_coordinate_from_dict(b.lower(), is_dimension=True, **dimensions[key])

        column_counts = file.column_header_counts

        # Add in the spatio-temporal coordinates
        for key in list(coordinates.keys()):
            coord = coordinates[key].strip()
            discrete = key in ('x', 'y', 'z', 't')

            assert coord in file.metadata, ValueError(f"Missing metadata for coordinate {key}")

            # remove the coord from column counts & metadata, so doesn't get added again later
            column_counts.pop(coord, None)
            coord_meta, _ = file.metadata.pop_and_split((coord,))
            # Might need to handle already added coords from the dimensions dict.
            self._obj = self.add_coordinate_from_values(key.lower(),
                                            values=file.df[coord].values,
                                            dimensions=["index"],
                                            discrete = discrete,
                                            is_projected = self.is_projected,
                                            is_dimension=False,
                                            **coord_meta[coord])


        # Combine the column headers in the file with keys from the json metadata
        # If there is a variable with raw columns specified, we need to remove those individual columns
        # Otherwise they are duplicated.
        for key, item in file.metadata.items():
            if key not in column_counts:
                if 'raw_data_columns' in item:
                    for raw_key in item['raw_data_columns']:
                        del column_counts[raw_key]
                column_counts[key] = 0

        # Now we have all dimensions and coordinates defined.
        # Start adding the data variables
        for var in column_counts:

            assert var in file.metadata, ValueError(f"Missing metadata for variable {var}")
            var_meta = file.metadata[var]

            # check system couplet labels
            if "system_couplet" in var_meta:
                couplet_labels = cls._couplet_labels(system)

                if len(couplet_labels) == 0:
                    raise ValueError(f"A system couplet exists for variable {var} but no system is passed")

                if var_meta["system_couplet"] not in couplet_labels:
                    raise ValueError(f"variable {var} has a system_couplet value that does not match any couplet labels: {couplet_labels}")


            if not var in coordinates.keys():
                all_columns = sorted(list(file.df.columns))

                # Use a column from the CSV file and add it as a variable
                if var in all_columns:
                    self._obj = self.add_variable_from_dict(var.lower(),
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

                        # # Check whether the column header starts with 1 or 0
                        # starts_from_one = not ((f"{var}[0]" in file.df) or (f"{var}_0" in file.df))

                        # # Get which type of header delim is used for multi column variables
                        # delim = "[]" if f"{var}[{starts_from_one}]" in file.df else "_"

                        # key = "{0}[{1}]" if delim == "[]" else "{0}_{1}"
                        # values = file.df[[key.format(var, i+starts_from_one) for i in range(column_counts[var])]].values

                        # {variable}_[0], {variable}_[1], {variable}_[2], ...
                        bracket_pat = re.compile(rf"^{re.escape(var)}\[(\d+)\]$")
                        bracket_matches = column_matches(bracket_pat, file.df.columns)

                        # {variable}_0, {variable}_1, {variable}_2, ...
                        underscore_pat = re.compile(rf"^{re.escape(var)}_(\d+)$")
                        underscore_matches = column_matches(underscore_pat, file.df.columns)

                        # Decide the format, assert if neither format is present
                        if bracket_matches:
                            matches = bracket_matches
                        elif underscore_matches:
                            matches = underscore_matches
                        else:
                            raise AssertionError(f"No columns found for '{var}' in either '{var}[i]' or '{var}_i' format.")

                        # ensure columns are sorted numerically and find start/end
                        matches.sort(key=lambda x: x[1])          # sort by captured integer
                        matches = [label for label, idx in matches]
                        values = file.df[matches].values

                        # # try:
                        # if delim == "[]":
                        #     values = file.df[[f"{var}[{i+starts_from_one}]" for i in range(column_counts[var])]].values
                        # else:
                        #     values = file.df[[f"{var}_{i+starts_from_one}" for i in range(column_counts[var])]].values
                        # except KeyError:
                        #     raise KeyError(f"Column header names for variable '{var}' not found in {var}[0] or {var}_0 format")

                    if values is not None:
                        # assert values is not None, ValueError((f'{var} not in data file, double check, '
                        #                                     'raw_data_columns field required in variables '
                        #                                     'if combining unique columns to a new variable without an [i] increment'))

                        assert 'dimensions' in var_meta, ValueError(f'No dimensions found for 2+ dimensional variable {var}.  Please add "dimensions":[---, ---]')

                        # Check for the dimensions of the variable and try adding from a system class.
                        # system = kwargs.get('system', None)

                        # Take any dimension we do not have yet from the system it
                        # belongs to, e.g. the gate times a set of channels sits on.
                        for dim in var_meta['dimensions']:
                            dl = dim.lower()
                            if dl not in self._obj.dims:
                                coordinate = cls._system_coordinate(system, dl)
                                if coordinate is not None:
                                    self._obj = self._obj.assign_coords({dl: coordinate})

                        assert all([dim.lower() in self._obj.dims for dim in var_meta['dimensions']]), ValueError(f"Could not match dimensions for variable {var} with metadata dimensions {var_meta['dimensions']}. Dimensions already attached are: {list(self._obj.dims)}")

                        self._obj = self.add_variable_from_dict(var.lower(), values=values, **var_meta)



        # add global attrs to tabular, skip variables and dimensions
        kwargs = Metadata(json_md['dataset_attrs'])
        kwargs["structure"] = "tabular"
        kwargs.check_keys(cls.required_metadata)

        self.attrs = kwargs

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

            out = f"i{large%10 + p1}"
        if dtype == np.float32:
            out = default_f32
        if dtype == np.float64:
            out = default_f64

        if values.ndim == 2:
            out = f"{values.shape[1]}" + out

        return out

    def to_file(self, filename, **kwargs):
        """Write this dataset out in one of the tabular file formats."""
        handler = handler_for(filename, file_type=kwargs.pop('file_type', None))

        handler.to_file(self, filename, **kwargs)