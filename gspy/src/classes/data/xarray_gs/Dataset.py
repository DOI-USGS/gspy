import os
import json
import matplotlib.pyplot as plt

from pprint import pprint
import numpy as np
from numpy import all, arange, asarray, diff, median, r_, zeros
from xarray import DataArray as xr_DataArray
from xarray import open_dataset
from .DataArray import DataArray
from .Coordinate import Coordinate

from ....utilities import flatten, unflatten, load_metadata_from_file, check_key_whitespace
from ...survey.Spatial_ref import Spatial_ref

from xarray import register_dataset_accessor

@register_dataset_accessor('gs_dataset')
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

    @classmethod
    def open_dataset(cls, *args, **kwargs):
        """Open (lazy loading) a netcdf.

        Wraps around the xarray open_dataset but forces xarray to honour gate times and the CF convention.

        Returns
        -------
        xarray.Dataset
            Native xrray Dataset
        """
        kwargs['decode_times'] = kwargs.get('decode_times', False)
        kwargs['decode_cf'] = kwargs.get('decode_cf', True)
        return open_dataset(*args, **kwargs)

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

        return self

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

        tmp = Coordinate.from_dict(name, self.is_projected, is_dimension=is_dimension, **kwargs)
        # Add the actual coordinate values
        self._obj[name] = tmp

        # Add the bounds of the coordinate
        if not discrete or bounding_dict['bounds'] is not None:
            self = self.add_bounds_to_coordinate(name, **bounding_dict)

        return self

    def add_coordinate_from_values(self, name, values, discrete=False, is_dimension=False, **kwargs):
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

        self._obj[name] = Coordinate.from_values(name, values, is_dimension=is_dimension, **kwargs)
        self._obj = self._obj.assign_coords({name : self._obj[name]})

        # Add the bounds of the coordinate
        if not discrete:
            self = self.add_bounds_to_coordinate(name, **bounding_dict)

        return self

    def add_variable_from_values(self, name, values, **kwargs):
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
        tmp = tuple([self._obj[vdim].size for vdim in kwargs['dimensions']])
        assert all(values.shape == tmp), ValueError("Shape {} of variable {} does not match specified dimensions {} with shape {}".format(values.shape, name, kwargs['dimensions'], tmp))

        kwargs['coords'] = [self._obj.coords[dim] for dim in kwargs['dimensions']]
        self._obj[name] = DataArray.from_values(name, values, **kwargs)

        return self

    def _add_nv(self):
        """Adds a required dimension to the Dataset when bounds need to be specified.

        Returns
        -------
        _type_
            _description_
        """
        if not 'nv' in self._obj:
            self = self.add_coordinate_from_values('nv',
                                                   r_[0, 1],
                                                   is_projected=False,
                                                   is_dimension=True,
                                                   discrete=True,
                                                   **dict(standard_name = 'number_of_vertices',
                                                          long_name = 'Number of vertices for bounding variables',
                                                          units = 'not_defined',
                                                          null_value = 'not_defined'))
        return self._obj

    def read_metadata(self, filename):
        """Read json metadata file

        Parameters
        ----------
        filename : str
            Json file

        Returns
        -------
        dic : dict
            Dictionary of JSON metadata

        """
        if filename == 'None':
            return

        if filename is None:
            self.write_metadata_template(filename)
            raise Exception("Please re-run and specify metadata when instantiating {}".format(self.__class__.__name__))

        # reading the data from the file
        dic = load_metadata_from_file(filename)

        flag = check_key_whitespace(dic)
        assert not flag, Exception("Metadata file {} has keys with whitespace.  Please remove spaces")

        if 'coordinates' in dic:
            for key, value in dic['coordinates'].items():
                dic['coordinates'][key] = value.strip()

        return dic

    @classmethod
    def open_netcdf(cls, filename, group, **kwargs):
        """Read Data from a netcdf file using xrray's lazy open_dataset

        Parameters
        ----------
        filename : str
            Path to the netcdf file
        group : str
            Netcdf group name containing Dataset

        Returns
        -------
        Dataset

        """
        return Dataset.open_dataset(filename, group=group.lower(), **kwargs)

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
            xlabel = "Distance ({})".format(self._obj['x'].attrs['units'])
        else:
            x = self._obj[x]
            xlabel = 'x\n{}'.format(self._obj['x'].gs_dataarray.label)

        splot = plt.plot(x, self._obj[hue].values, **kwargs)

        plt.xlabel(xlabel)
        plt.ylabel('y\n{}'.format(self._obj[hue].gs_dataarray.label))

        # cb=plt.colorbar()
        # cb.set_label(r'{}\n{} [{}]'.format(variable, self._obj[variable].attrs['long_name'], self._obj[variable].attrs['units']), rotation=-90, labelpad=30)
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

            plt.xlabel('x\n{} [{}]'.format(x.attrs['long_name'], x.attrs['units']))
            plt.ylabel('y\n{} [{}]'.format(y.attrs['long_name'], y.attrs['units']))

            cb=plt.colorbar()
            cb.set_label('{}\n{} [{}]'.format(hue, self._obj[hue].attrs['long_name'], self._obj[hue].attrs['units']), rotation=-90, labelpad=30)

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

        return self

    def update_attrs(self, **kwargs):
        """Adds metadata from Json with keys flattened. This is the only way to add nested metadata as dicts into xarray attrs.
        """
        kwargs = flatten(kwargs, '', {})
        self._obj.attrs.update(kwargs)

    def write_netcdf(self, filename, group, **kwargs):
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
                # if 'grid_mapping' in self._obj[var].attrs:
                #     del self._obj[var].attrs['grid_mapping']

        self._obj.to_netcdf(filename, mode=mode, group=group, format='netcdf4', engine='netcdf4', **kwargs)

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

    def write_ncml(self, filename, group, index):
        """Write an NCML file

        Parameters
        ----------
        filename : str
            NCML filename
        group : str
            Group name in Netcdf file to generate NCML output for.
        index : str
            todo
        """

        infile = '{}.ncml'.format('.'.join(filename.split('.')[:-1]))
        if not os.path.isfile(infile):
            print('original file not found!')
            singleflag=True
            sp1, sp2 = '', '  '
            f = open(infile, 'w')
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" location="{}.nc">\n\n'.format(filename.split(os.sep)[-1]))
            f.write('{}<group name="/{}">\n\n'.format(sp1, group))
            f.write('{}<group name="/{}">\n\n'.format(sp2, index))
            f.close()
        else:
            singleflag=False
            sp1, sp2 = '  ', '    '

        f = open(infile, 'a')
        ### Dimensions:
        for dim in self._obj.dims:
            f.write('%s<dimension name="%s" length="%s"/>\n' % (sp2, dim, self._obj.dims[dim]))
        f.write('\n')

        ### Global Attributes:
        for attr in self._obj.attrs:
            att_val = self._obj.attrs[attr]
            if '"' in str(att_val):
                att_val = att_val.replace('"',"'")
            f.write('%s<attribute name="%s" value="%s"/>\n' % (sp2, attr, att_val))
        f.write('\n')

        ### Variables:
        for var in self._obj.variables:
            tmpvar = self._obj.variables[var]
            dtype = str(tmpvar.dtype).title()[:-2]
            if var == 'crs' or dtype == 'object':
                f.write('%s<variable name="%s" shape="%s" type="String">\n' % (sp2, var, " ".join(tmpvar.dims)))
            else:
                f.write('%s<variable name="%s" shape="%s" type="%s">\n' % (sp2, var, " ".join(tmpvar.dims), dtype))
            for attr in tmpvar.attrs:
                att_val = tmpvar.attrs[attr]
                if '"' in str(att_val):
                    att_val = att_val.replace('"',"'")
                f.write('%s%s<attribute name="%s" type="String" value="%s"/>\n' % (sp1, sp2, attr, att_val))
            f.write('%s</variable>\n\n' % sp2)

        if singleflag:
            f.write('{}</group>\n\n'.format(sp2))
            f.write('{}</group>\n\n'.format(sp1))
            f.write('</netcdf>')

        f.close()
