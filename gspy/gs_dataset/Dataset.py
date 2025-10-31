import os
import json
import matplotlib.pyplot as plt

from pprint import pprint
import numpy as np
from numpy import all, arange, asarray, diff, median, r_, zeros
from datetime import datetime
from ..gs_dataarray.DataArray import DataArray
from ..gs_dataarray.Coordinate import Coordinate

from ..utilities import same_length_lists, deprecated
from ..metadata.Metadata import Metadata
from ..gs_dataarray.Spatial_ref import Spatial_ref

from xarray import DataArray as xr_DataArray
from xarray import Dataset as xr_Dataset
from xarray import register_dataset_accessor


@register_dataset_accessor('gs')
class Dataset:
    """Accessor to xarray.Dataset to better handle coordinates/dimensions and variables that honour the CF convention.

    Checks necessary metadata to satisfy the CF convention, and allows use with GIS software.

    Returns
    -------
    out : xarray.Dataset

    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def is_projected(self):
        """Does the dataset have a projected spatial reference

        Returns
        -------
        out : bool

        """
        if not 'spatial_ref' in self._obj:
            return False
        return self._obj['spatial_ref'].attrs['grid_mapping_name'] != "lattitude longitude"

    @property
    def json_metadata(self):
        return self._json_metadata

    @json_metadata.setter
    def json_metadata(self, value):
        assert isinstance(value, dict), TypeError('json_metadata must have type dict')
        self._json_metadata = value

    @property
    def spatial_ref(self):
        return self._obj['spatial_ref']

    def add_bounds_to_coordinate(self, name, **kwargs):
        """Adds bounds to a coordinate.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the bounds will not be added correctly.

        Parameters
        ----------
        name : str
            Name of the variable to add bounds to.

        Returns
        -------
        Dataset
            Dataset with added bounds.

        """

        # The bounds are 2xN and need their own "nv" dimension
        self._obj = self._add_nv()

        # Now add the bound
        self._obj[name + '_bnds'] = DataArray.add_bounds_to_coordinate_dimension(self._obj[name],
                                                                               name,
                                                                               dims = (*[dim for dim in self._obj[name].dims], 'nv'),
                                                                               coords=(*[self._obj[dim] for dim in self._obj[name].dims], self._obj['nv']),
                                                                               **kwargs)
        self._obj[name].attrs['bounds'] = name + '_bnds'

        return self._obj

    def add_coordinate_from_dict(self, name, discrete=False, is_dimension=False, **kwargs):
        """Attach a coordinate/dimension to a Dataset from a dictionary.

        The DataSet is returned with the coordinate attached. Bounds are also added to the Dataset if this
        coordinate is not discrete.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the coordinate will not be added correctly.

        Parameters
        ----------
        name : str
            Name of the coordinate
        discrete : bool, optional
            Is this coordinate discrete? by default False
        is_dimension : bool, optional
            Is this a coordinate-dimension? by default False

        Returns
        -------
        Dataset
            Dataset with added coordinate.

        See Also
        --------
        .Coordinate.Coordinate.from_dict : for pertinent Coordinate keywords and metadata

        """

        bounding_dict = dict(bounds = kwargs.pop('bounds', None))

        values = kwargs.pop('values', kwargs.pop('centers', None))

        if values is None:
            return self.add_coordinate_from_dict_np(name, discrete, is_dimension, values=values, **kwargs)

        if not same_length_lists(values): # Assume non 1D is list of lists.
            assert 'label' in kwargs, ValueError(f"Need label in metadata for coordinate inhomogenous sized lists {name}")
            prefix = kwargs.pop('prefix', None); prefix = "" if prefix is None else f"{prefix}_"

            for this, label in zip(values, kwargs.pop('label')):
                label = f"{prefix}{label}".lower()

                kwargs['values'] = this
                self._obj = self.add_coordinate_from_dict_np(f"{label}_{name}", discrete, is_dimension, **kwargs)
        else:
            self._obj = self.add_coordinate_from_dict_np(name, discrete, is_dimension, values=values, **kwargs)

        return self._obj


    def add_coordinate_from_dict_np(self, name, discrete=False, is_dimension=False, **kwargs):
        """Attach a coordinate/dimension to a Dataset from a dictionary.

        The DataSet is returned with the coordinate attached. Bounds are also added to the Dataset if this
        coordinate is not discrete.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the coordinate will not be added correctly.

        Parameters
        ----------
        name : str
            Name of the coordinate
        discrete : bool, optional
            Is this coordinate discrete? by default False
        is_dimension : bool, optional
            Is this a coordinate-dimension? by default False

        Returns
        -------
        Dataset
            Dataset with added coordinate.

        See Also
        --------
        .Coordinate.Coordinate.from_dict : for pertinent Coordinate keywords and metadata

        """
        bounding_dict = dict(bounds = kwargs.pop('bounds', None))
        kwargs['is_projected'] = kwargs.pop('is_projected', self.is_projected)
        name = name.lower()

        # Add the actual coordinate values
        self._obj[name] = Coordinate.from_dict(name, is_dimension=is_dimension, **kwargs)

        # Add the bounds of the coordinate
        if not discrete or bounding_dict['bounds'] is not None:
            self._obj = self.add_bounds_to_coordinate(name, **bounding_dict)

        return self._obj

    def add_coordinate_from_values(self, name, discrete=False, is_dimension=False, **kwargs):
        """Attach a coordinate/dimension to a Dataset using an array of values defining center values.

        The DataSet is returned with the coordinate attached. Bounds are also added to the Dataset if this
        coordinate is not discrete.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the coordinate will not be added correctly.

        Parameters
        ----------
        name : str
            Name of the coordinate
        discrete : bool, optional
            Is this coordinate discrete? by default False
        is_dimension : bool, optional
            Is this a coordinate-dimension? by default False

        Returns
        -------
        Dataset
            Dataset with added coordinate.

        See Also
        --------
        .Coordinate.Coordinate.from_values : for pertinent Coordinate keywords and metadata

        """
        bounding_dict = dict(bounds = kwargs.pop('bounds', None))

        if (not is_dimension) and ('dimensions' in kwargs):
            kwargs['coords'] = kwargs.pop('coords', {key:self._obj[key] for key in kwargs['dimensions']})

        self._obj[name] = Coordinate.from_values(name, is_dimension=is_dimension, **kwargs)
        self._obj = self.assign_coords(name, name, discrete, **bounding_dict)

        return self._obj

    def add_dimensions_from_variables(self, **kwargs):
        # Create any dimensions for those referenced in the metadata dims.
        for variable in list(kwargs.keys()):
            v = kwargs[variable]
            if isinstance(v, dict):
                if 'dimensions' in v:
                    dimensions = v['dimensions']
                    if not isinstance(dimensions, list):
                        dimensions = [dimensions]

                    for dimension in dimensions:
                        if dimension not in self._obj:
                            assert dimension in kwargs, ValueError((f"dimension {dimension} specified in metadata for {variable}"
                                                                "but was not defined in either the 'dimensions' section or the 'variable' section"))
                            dim_to_add = kwargs.pop(dimension, {})
                            assert 'values' in dim_to_add, ValueError("Dimensions that are defined in the variables section must be nested with values and more metadata defined i.e. long_name, null_value, units")
                            self._obj = self.add_coordinate_from_dict(name=dimension,
                                                                    label=kwargs.get('label', None),
                                                                    prefix=kwargs.get('prefix', None),
                                                                    is_dimension=True,
                                                                    discrete=True,
                                                                    **dim_to_add)

        return self, kwargs

    def assign_coords(self, coord, data_var, discrete=False, **kwargs):
        self._obj = self._obj.assign_coords({coord : self._obj[data_var]})
        if coord in ['x','y','z','t']:
            self._obj[coord].attrs.update({'axis':coord.upper()})
        # Add the bounds of the coordinate
        if not discrete:
            self._obj = self.add_bounds_to_coordinate(coord, **kwargs)
        return self._obj

    @deprecated
    def add_variable_from_values(self, name, **kwargs):
        return self.add_variable_from_dict(name, **kwargs)

    def add_variable_from_dict(self, name, **kwargs):
        values = kwargs.pop('values', None)
        if values is None:
            return self.add_variable_from_dict_np(name, values=values, **kwargs)

        # Catch scalars
        if not isinstance(values, list):
            return self.add_variable_from_dict_np(name, values=values, **kwargs)

        # Catch homogenous shape arrays.
        if same_length_lists(values): # Assume non 1D is list of lists.
            return self.add_variable_from_dict_np(name, values=values, **kwargs)

        # Catch non-uniform sized lists of array
        assert 'label' in kwargs, ValueError(f"Need label in metadata for coordinate inhomogenous sized lists {name}")
        dimensions = kwargs.pop('dimensions')[1]
        for this, label in zip(values, kwargs.pop('label')):
            if 'prefix' in kwargs:
                label = f"{kwargs['prefix']}_{label}".lower()

            kwargs['values'] = this
            self._obj = self.add_variable_from_dict_np(f"{label}_{name}", dimensions=f"{label}_{dimensions}", **kwargs)
        return self._obj

    def add_variable_from_dict_np(self, name, **kwargs):
        """Add a variable to the Dataset

        Automatically maintains coords on the variable given its dims.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the variable will not be added correctly.

        Parameters
        ----------
        name : str
            Name of the variable
        values : array_like
            Values of the variable

        Returns
        -------
        Dataset
            Dataset with variable added.

        Raises
        ------
        ValueError
            If the shape of the values does not match the specified dimensions.

        """
        values = kwargs['values']

        # Add dimensions from metadata to the Dataset
        if "dimensions" in kwargs:
            if isinstance(kwargs['dimensions'], str):
                kwargs['dimensions'] = [kwargs['dimensions']]


            tmp = tuple([self._obj[vdim.lower()].size for vdim in kwargs['dimensions']])
            shp = np.shape(values)

            if len(tmp) != len(shp):
                if tmp[0] == 1:
                    shp = np.r_[1, *shp]

            shape_check = [x==y for x, y in zip(shp, tmp)]

            for i, good in enumerate(shape_check):
                dim = kwargs['dimensions'][i]
                assert good, ValueError(f"Size of data for variable {name} along dimension {dim} is {shp[i]} and does not match xarray dimension with size {tmp[i]}")

            kwargs['coords'] = {dim: self._obj.coords[dim.lower()] for dim in kwargs['dimensions']}

        if 'prefix' in kwargs:
            name = f"{kwargs.pop('prefix')}_{name}".lower()

        # drop label
        if 'label' in kwargs:
            kwargs.pop('label')

        self._obj[name] = DataArray.from_values(name, **kwargs)

        return self._obj

    def _add_nv(self):
        """Adds a required dimension to the Dataset when bounds need to be specified.

        Returns
        -------
        _type_
            _description_
        """
        if not 'nv' in self._obj:
            self._obj = self._obj.gs.add_coordinate_from_dict('nv',
                                                   values=r_[0, 1],
                                                   is_projected=False,
                                                   is_dimension=True,
                                                   discrete=True,
                                                   standard_name = 'number_of_vertices',
                                                   long_name = 'Number of vertices for bounding variables',
                                                   units = 'not_defined',
                                                   null_value = 'not_defined')
        return self._obj

    # def read_metadata(self, filename):
    #     """Read json metadata file

    #     Parameters
    #     ----------
    #     filename : str
    #         Json file

    #     Returns
    #     -------
    #     dic : dict
    #         Dictionary of JSON metadata

    #     """
    #     if filename == 'None':
    #         return

    #     if filename is None:
    #         self.write_metadata_template(filename)
    #         raise Exception("Please re-run and specify metadata when instantiating {}".format(self.__class__.__name__))

    #     # reading the data from the file
    #     dic = load_metadata_from_file(filename)

    #     flag = check_key_whitespace(dic)
    #     assert not flag, Exception("Metadata file {} has keys with whitespace.  Please remove spaces")

    #     if 'coordinates' in dic:
    #         for key, value in dic['coordinates'].items():
    #             dic['coordinates'][key] = value.strip()

    #     if "variables" in dic:
    #         dic['variables'] = {key.lower():item for key, item in dic['variables'].items()}

    #     return dic

    @staticmethod
    def metadata_template(data_filename=None, metadata_file=None, **kwargs):

        system = kwargs.get('system', {})
        json_md = Metadata()

        system_metadata = {}
        if metadata_file is not None:
            # assert metadata_file is not None, ValueError("metadata_file not specified")
            json_md = Metadata.read(metadata_file)

            # No systems were passed through, try to read from metadata
            if len(system) == 0:
                for key in list(json_md.keys()):
                    if "system" in key:
                        system[key] = json_md.pop(key)

                # Systems were found, create a System datatree/dataset
                from ..gs_datatree.Container import Container
                if len(system) > 0:
                    system_metadata[key] = system
                    system, _ = Container.Systems(**system)


        # Attach apriori given system dict
        kwargs['system'] = system

        from .Tabular import Tabular
        out = Tabular.metadata_template(data_filename,  metadata_file=json_md, **kwargs)
        out = Metadata.merge(out, system_metadata)

        return out

    def plot(self, hue, **kwargs):
        """Scatter plot of variable against x, y co-ordinates

        Parameters
        ----------
        variable : str
            Xarray Dataset variable name

        Returns
        -------
        ax : matplotlib.Axes
            Figure handle
        sc : xarray.plot.scatter
            Plotting handle

        """
        ax = kwargs.pop('ax', plt.gca())

        x = kwargs.pop('x', 'x')

        if x == 'distance':
            x, y = self._obj['x'].values, self._obj['y'].values
            x = np.hstack([0.0, np.sqrt(np.cumsum(np.diff(x))**2.0 + np.cumsum(np.diff(y))**2.0)])
            xlabel = f"Distance ({self._obj['x'].attrs['units']})"
        else:
            x = self._obj[x]
            xlabel = f'x\n{self._obj['x'].gs.label}'

        splot = plt.plot(x, self._obj[hue].values, **kwargs)

        plt.xlabel(xlabel)
        plt.ylabel(f'y\n{self._obj[hue].gs.label}')

        plt.tight_layout()

        return ax, splot

    def scatter(self, **kwargs):
        """Scatter plot of variable against x, y co-ordinates

        Parameters
        ----------
        variable : str
            Xarray Dataset variable name

        Returns
        -------
        ax : matplotlib.Axes
            Figure handle
        sc : xarray.plot.scatter
            Plotting handle

        """
        ax = kwargs.pop('ax', plt.gca())

        x = kwargs.pop('x', 'x')
        y = kwargs.pop('y', 'y')

        hue = kwargs.pop('hue', None)


        if hue is None:
            return self.plot(x=x, hue=y, **kwargs)

        else:

            x = self._obj[kwargs.pop('x', 'x')]
            y = self._obj[kwargs.pop('y', 'y')]

            splot = plt.scatter(x.values, y.values, c=self._obj[hue].values, **kwargs)

            plt.xlabel(f'x\n{x.attrs['long_name']} [{x.attrs['units']}]')
            plt.ylabel(f'y\n{y.attrs['long_name']} [{y.attrs['units']}]')

            cb=plt.colorbar()
            cb.set_label(f'{hue}\n{self._obj[hue].attrs['long_name']} [{self._obj[hue].attrs['units']}]', rotation=-90, labelpad=30)

            plt.tight_layout()

        return ax, splot

    def set_spatial_ref(self, kwargs):
        """Set the spatial ref of the Dataset.

        Specifically adds an xarray coordinate called 'spatial_ref' which is required for GIS software and the CF convention.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the spatial_ref will not be added correctly.

        Parameters
        ----------
        kwargs : dict, gspy.Spatial_ref, or xarray.DataArray
            * If dict: creates a Spatial_ref from a dict of metadata.
            * If an existing spatial ref, assign by reference

        Returns
        -------
        Dataset
            Dataset with spatial_ref added.

        See Also
        --------
        ...Survey.Spatial_ref : for more details of creating a Spatial_ref

        """
        if not ('spatial_ref' in self._obj):
            assert isinstance(kwargs, (dict, Spatial_ref, xr_DataArray)), TypeError("spatial_ref must have type (dict, gspy.Spatial_ref)")
            if isinstance(kwargs, dict):
                crs = Spatial_ref.from_dict(kwargs)
            else:
                crs = kwargs # This is a pre-existing Spatial_ref/DataArray

            self._obj['spatial_ref'] = crs
            self._obj = self._obj.assign_coords({'spatial_ref' : crs})

        return self._obj

    def update_attrs(self, key='', **kwargs):
        """Adds metadata from Json with keys flattened. This is the only way to add nested metadata as dicts into xarray attrs.
        """
        self._obj.attrs.update(Metadata(kwargs).flatten())

    def to_netcdf(self, *args, **kwargs):
        """Write the survey to a netcdf file

        Parameters
        ----------
        args : list
            Arguments to pass to xarray.Dataset.to_netcdf
        kwargs : dict
            Keyword arguments to pass to xarray.Dataset.to_netcdf

        Returns
        -------
        None

        """
        kwargs["format"] = kwargs.get("format", "NETCDF4")
        kwargs["engine"] = kwargs.get("engine", "h5netcdf")

        self._obj.to_netcdf(*args, **kwargs)


    # def write_netcdf(self, filename, group, **kwargs):
    #     """Write to netcdf file

    #     Parameters
    #     ----------
    #     filename : str
    #         Path to the file
    #     group : str
    #         Netcdf group name to write to

    #     """
    #     mode = 'a' if os.path.isfile(filename) else 'w'
    #     if 'raster' in group:
    #         for var in self._obj.data_vars:
    #             if self._obj[var].attrs['null_value'] != 'not_defined':
    #                 self._obj[var].attrs['_FillValue'] = self._obj[var].attrs['null_value']
    #             # if 'grid_mapping' in self._obj[var].attrs:
    #             #     del self._obj[var].attrs['grid_mapping']

    #     kwargs['engine'] = kwargs.get('engine', 'h5netcdf')
    #     kwargs['format'] = kwargs.get('format', 'netcdf4')

    #     self._obj.to_netcdf(filename, mode=mode, group=group, **kwargs)

    def write_zarr(self, filename, group, **kwargs):
        """Write to netcdf file

        Parameters
        ----------
        filename : str
            Path to the file
        group : str
            Netcdf group name to write to

        """
        mode = 'a' if os.path.isfile(filename) else 'w'
        if 'raster' in group:
            for var in self._obj.data_vars:
                if self._obj[var].attrs['null_value'] != 'not_defined':
                    self._obj[var].attrs['_FillValue'] = self._obj[var].attrs['null_value']
                if 'grid_mapping' in self._obj[var].attrs:
                    del self._obj[var].attrs['grid_mapping']

        self._obj.to_zarr(filename, mode=mode, group=group, **kwargs)

    def write_ncml(self, file, name, indent, no_end=False):

        st = "  "*indent

        file.write(f'{st}<group name="/{name}">\n')
        si = "  "*(indent+1)

        if len(self._obj.dims) > 0:
            for dim in self._obj.dims:
                file.write(f'{si}<dimension name="{dim}" length="{self._obj.sizes[dim]}"/>\n')
            file.write("\n")

        if len(self._obj.attrs) > 0:
            for k, v in self._obj.attrs.items():
                if '"' in str(v):
                    v = v.replace('"',"'")
                file.write(f'{si}<attribute name="{k}" value="{str(v).strip('\n')}"/>\n')
            file.write('\n')

        if len(self._obj.variables) > 0:
            for var in self._obj.variables:
                self._obj[var].gs.write_ncml(file, indent)

        if not no_end:
            file.write(f'{st}</group>\n')

    @classmethod
    def Survey(cls, **kwargs):
        """Attach an xarray.Dataset containing GS metadata or create one from a dict

        Parameters
        ----------
        kwargs : xarray.Dataset or dict
            * If xarray.Dataset checks for required metadata and spatial_ref
            * If dict, checks for required metadata and a spatial_ref definition

        See Also
        --------
        ...Survey.Spatial_ref : for more details of creating a Spatial_ref

        """

        required = ("title", "institution", "source", "history", "references")
        if isinstance(kwargs, xr_Dataset):
            assert all([x in kwargs.attrs for x in required]), ValueError(f"Dataset.attrs must contain at least {required}")
            xarray = kwargs
        else:

            assert isinstance(kwargs, dict), TypeError('metadata must have type dict')
            assert "dataset_attrs" in kwargs, ValueError("Survey metadata must contain entry 'dataset_attrs")
            assert "spatial_ref" in kwargs, ValueError("Survey metadata must contain entry 'spatial_ref")
            assert all([x in kwargs["dataset_attrs"] for x in required]), ValueError(f"dataset_attrs must contain at least {required}")

            ds = cls(xr_Dataset(attrs = {}))

            ds.update_attrs(**kwargs["dataset_attrs"])

            for key in kwargs:
                if key not in ('spatial_ref', 'dataset_attrs'):
                    tmpdict2 = {k: v for k, v in kwargs[key].items() if v}
                    tmpdict2 = Metadata(tmpdict2).flatten()

                    for k,v in tmpdict2.items():
                        if isinstance(v,list):

                            if isinstance(v[0],list):
                                tmpdict2[k] = str(v)
                    ds._obj[key] = xr_DataArray(attrs=tmpdict2)

            ds._obj = ds.set_spatial_ref(kwargs['spatial_ref'])

            return ds._obj

    def subset(self, key, value, **kwargs):
        return self._obj.where(self._obj[key]==value, **kwargs)

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

        x = subset.gs.x_axis(kwargs.pop('axis', 'x'))

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
            from ..utilities.maths import haversine_distance
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

    def add_timestamp(self, key='datetime', date='date', time='time', datum='1900-01-01', date_format = None):
        """Combine date and time strings into a numeric datetime
        as decimal days since datum or date-zero, add as "t" axis.

        Parameters
        ----------
        date : str
            date , if date_format is None then it can be formatted: 'YYYY-MM-DD', 'YYYY/MM/DD', 'MM-DD-YYYY', or 'MM/DD/YYYY'
        time : str
           time in format 'HH:MM:SS' or 'HH:MM:SS.sss'
        datum: str
            date and time of date-zero in format 'YYYY-MM-DD', default is '1900-01-01'
        date_format : str
            custom format for date such as 'DD/MM/YYYY'

        Returns
        -------
        self._obj
            with numeric timestamp array added to variables.
        """
        assert not key in self._obj.variables, ValueError(f"Variable {key} already exists in dataset")

        # Parse the date and time strings
        d = self._obj[date].values.astype(str)

        # Determine timestamp from dictionary formats
        if date_format == None:
            yr = "%Y?%m?%d"
            mo = "%m?%d?%Y"
            da = "%d?%m?%Y"

            dlim = '-' if '-' in d[0] else '/'
            splt = d[0].split(dlim)
            fmt = yr if len(splt[0]) == 4 else da
            # try to detect month first
            if fmt == da:
                if splt[1] > 12:
                    fmt = mo
                for i in range(len(d)):
                    if d[i].split(dlim)[1] > 12:
                        fmt = mo
                        break

            date_format = fmt.replace("?", dlim)

        t = self._obj[time].values.astype(str)
        time_format = "%H:%M:%S.%f" if '.' in t[0] else "%H:%M:%S"

        # Combine date and time and save datetime as a variable with a T coordinate
        combined_datetime = [datetime.strptime(f"{d[i]} {t[i]}", f"{date_format} {time_format}") for i in range(len(d))]

        datum_datetime = np.datetime64(datetime.strptime(datum,'%Y-%m-%d'))

        dt = (np.array(combined_datetime,dtype='datetime64[s]') - datum_datetime)/np.timedelta64(1,'D')

        varmeta = {"standard_name": key,
                   "long_name":"Time, decimal days",
                   "units":"day",
                   "null_value":"not_defined",
                   "datum":datum}

        self = self.add_variable_from_values(key, values=dt, dimensions='index', **varmeta)

        return self._obj

    def get_all_attr(self, attr, path, **kwargs):
        for key in self._obj.data_vars:
            attrs = self._obj[key].attrs
            if attr in attrs:
                kwargs[path+f"/{key}"] = attrs.get(attr)
        return kwargs

    # System specific accessors
    @property
    def component_labels(self):
        tx = self._obj['component_transmitters'].values
        rx = self._obj['component_receivers'].values

        out = []
        for t, r in zip(tx, rx):
                out.append(f"{t}_{r}")

        return out


