import os
import json
import matplotlib.pyplot as plt

from pprint import pprint
from numpy import all, arange, asarray, diff, median, r_, zeros
from xarray import DataArray, open_dataset
from .DataArray import DataArray
from .Coordinate import Coordinate

from ....utilities import flatten, unflatten
from ...survey.Spatial_ref import Spatial_ref

import xarray as xr

@xr.register_dataset_accessor('gs_dataset')
class Dataset:
    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        # self._spatial_ref = None

    @property
    def is_projected(self):
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
        """Loads a netcdf dataset using Xarray, but recasts it as our Dataset_gs class
        """
        return open_dataset(*args, **kwargs)

        # We need to copy the contents into a new class instiation of OUR type, since xr.load_dataset returns the parent of ourself.
        # return cls(
        #            #data_vars=tmp.data_vars,
        #            coords=tmp.coords,
        #            attrs=tmp.attrs)

    # This may not be needed
    # def _add_general_metadata(self, kwargs):
    #     kwargs = flatten(kwargs, '', {})
    #     self.attrs.update(kwargs)

    def add_coordinate_from_dict(self, name, discrete=False, is_dimension=False, **kwargs):
        """Attach a coordinate/dimension to a Dataset from a dictionary.

        If 'bounds' are not defined inside the dict, the coordinate is discrete.
        Otherwise, bounds are attached also in order to satisfy ???

        Parameters
        ----------
        name : str
            The name of the coordinate to attach

        Other Parameters
        ----------------
        standard_name : str
            CF convention standard name
        long_name : str
            CF convention long name
        units : str
            units of the coordinate
        null_value : int or float
            what are null values represented by
        centers : array_like
            Has shape (size of dimension, ) defining the center values of each "cell"
        bounds : array_like, optional
            Has shape (size of dimension, 2) defining the bounds of each "cell" in the coordinate

        Example
        -------
        depth_dict = {
                    "standard_name": "depth",
                    "long_name": "Depth below earth's surface DTM",
                    "units": "m",
                    "null_value": "not_defined",
                    # "bounds" : [[0, 5],
                    #             [5, 10]],
                    # "centers" : [2.5, 7.5, 20.0]}
        Dataset_gs.coordinate_from_dict('depth', **depth_dict)

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

        """IF its a dimension coordinate.  No need to specify dimensions, or coords.
           If its a non-dimensions coordinate. Need to specify dims.

        Returns
        -------
        _type_
            _description_
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
        assert all(values.shape == tuple([self._obj[vdim].size for vdim in kwargs['dimensions']])), ValueError("Shape {} of variable {} does not match specified dimensions with shape {}".format(values.shape, name, kwargs['dimensions']))

        kwargs['coords'] = [self._obj.coords[dim] for dim in kwargs['dimensions']]
        self._obj[name] = DataArray.from_values(name, values, **kwargs)

        return self

    def add_bounds_to_coordinate(self, name, **kwargs):

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

    def _add_nv(self):
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
        """Read metadata file

        Loads the metadata file and adds key_mapping values to property. If required dictionaries
        'raster_files' and/or 'variable_metadata' are missing, then a metadata template file is written
        and an error is triggered.

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
            self.write_metadata_template()
            raise Exception("Please re-run and specify supplemental information when instantiating Raster")

        # reading the data from the file
        with open(filename) as f:
            s = f.read()

        dic = json.loads(s)

        def check_key_whitespace(this, flag=False):
            if not isinstance(this, dict):
                return flag
            for key, item in this.items():
                if ' ' in key:
                    print('key "{}" contains whitespace. Please remove!'.format(key))
                    flag = True
                flag = check_key_whitespace(item, flag)
            return flag

        flag = check_key_whitespace(dic)
        assert not flag, Exception("Metadata file {} has keys with whitespace.  Please remove spaces")

        if 'coordinates' in dic:
            for key, value in dic['coordinates'].items():
                dic['coordinates'][key] = value.strip()

        return dic

    @classmethod
    def read_netcdf(cls, filename, group, spatial_ref=None, **kwargs):
        """Read Data from a netcdf file

        Parameters
        ----------
        filename : str
            Path to the netcdf file
        group : str
            Netcdf group name containing data.

        Returns
        -------
        out : gspy.Data

        """
        return open_dataset(filename, group=group.lower())

    def scatter(self, variable, **kwargs):
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
        return ax, plt.scatter(self._obj['x'].values, self._obj['y'].values, c=self._obj[variable].values, **kwargs)

    def set_spatial_ref(self, kwargs):
        if not ('spatial_ref' in self._obj):
            assert isinstance(kwargs, (dict, Spatial_ref, xr.DataArray)), TypeError("spatial_ref must have type (dict, gspy.Spatial_ref)")
            if isinstance(kwargs, dict):
                crs = Spatial_ref.from_dict(kwargs)
            else:
                crs = kwargs # This is a pre-existing Spatial_ref/DataArray

            self._obj['spatial_ref'] = crs
            self._obj = self._obj.assign_coords({'spatial_ref' : crs})

        return self

    def update_attrs(self, **kwargs):
        kwargs = flatten(kwargs, '', {})
        self._obj.attrs.update(kwargs)

    def write_netcdf(self, filename, group):
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
                #self.xarray[var].attrs['grid_mapping'] = self.xarray.spatial_ref.attrs['grid_mapping_name']
        self._obj.to_netcdf(filename, mode=mode, group=group, format='netcdf4', engine='netcdf4')

    def write_ncml(self, filename, group, index):
        """Write and NCML file

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