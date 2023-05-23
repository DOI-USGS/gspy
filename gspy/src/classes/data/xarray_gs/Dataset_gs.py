from copy import deepcopy
from pprint import pprint
from numpy import all, arange, asarray, diff, median, r_, zeros
from xarray import DataArray, Dataset, load_dataset
from .DataArray_gs import DataArray_gs

from ....utilities import flatten, unflatten
from ...survey.Spatial_ref import Spatial_ref

class Dataset_gs(Dataset):
    __slots__ = ()

    @classmethod
    def load_dataset(cls, *args, **kwargs):
        """Loads a netcdf dataset using Xarray, but recasts it as our Dataset_gs class
        """
        tmp = load_dataset(*args, **kwargs)

        # We need to copy the contents into a new class instiation of OUR type, since xr.load_dataset returns the parent of ourself.
        return cls(data_vars=tmp.data_vars,
                   coords=tmp.coords,
                   attrs=tmp.attrs)

    # This may not be needed
    # def _add_general_metadata(self, kwargs):
    #     kwargs = flatten(kwargs, '', {})
    #     self.attrs.update(kwargs)

    def add_coordinate_from_dict(self, name, discrete=False, **kwargs):
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
        # Add the actual coordinate values
        self[name] = DataArray_gs.coordinate_from_dict(name, discrete, self.is_projected, **kwargs)

        # Add the bounds of the coordinate
        if not discrete or bounding_dict['bounds'] is not None:
            self = self.add_bounds_to_coordinate(name, **bounding_dict)

        return self

    def add_coordinate_from_values(self, name, values, is_projected=False, discrete=False, **kwargs):
        
        if is_projected:
            if name in ('x', 'y'):
                kwargs['standard_name'] = "projection_{}_coordinate".format(name)

        bounding_dict = dict(bounds = kwargs.pop('bounds', None))

        self[name] = DataArray_gs.from_values(name, values, **kwargs)
        self = self.assign_coords({name : self[name]})

        # Add the bounds of the coordinate
        if not discrete:
            self = self.add_bounds_to_coordinate(name, **bounding_dict)

        
        return self

    def add_variable_from_values(self, name, values, **kwargs):
        assert all(values.shape == tuple([self[vdim].size for vdim in kwargs['dimensions']])), ValueError("Shape {} of variable {} does not match specified dimensions with shape {}".format(values.shape, name, kwargs['dimensions']))
        
        # store coordinate attributes
        dim_attrs = {dim: self[dim].attrs for dim in kwargs['dimensions']}

        self[name] = DataArray_gs.from_values(name, values, **kwargs)
        
        # reattach coordinate attributes
        for dim in kwargs['dimensions']:
            self[dim].attrs = dim_attrs[dim]

    def add_bounds_to_coordinate(self, name, **kwargs):

        # The bounds are 2xN and need their own "nv" dimension
        self = self._add_nv()

        # store nv dims
        nvdims = self['nv'].attrs
        
        # Now add the bound
        self[name + '_bnds'] = DataArray_gs.add_bounds_to_coordinate_dimension(self[name],
                                                                               name,
                                                                               **kwargs)
        self[name].attrs['bounds'] = name + '_bnds'

        # add nv dims back in
        self['nv'].attrs = nvdims

        return self

    def _add_nv(self):
        if not 'nv' in self:
            self = self.add_coordinate_from_values('nv',
                                                   r_[0, 1],
                                                   is_projected=False,
                                                   dimensions=['nv'],
                                                   discrete=True,
                                                   **dict(standard_name = 'number_of_vertices',
                                                          long_name = 'Number of vertices for bounding variables',
                                                          units = 'not_defined',
                                                          null_value = 'not_defined'))
        return self


    # @classmethod
    # def from_dict(cls, kwargs):
    #     from pprint import pprint
    #     pprint(kwargs)
    #     crs = kwargs.pop('spatial_ref', None)

    #     input('fdfdsfds')
    #     self = super(Dataset_gs, cls).from_dict(kwargs)
    #     self.spatial_ref = crs
    #     return self

    @property
    def is_projected(self):
        return self['spatial_ref'].attrs['grid_mapping_name'] != "lattitude longitude"

    @property
    def spatial_ref(self):
        return self['spatial_ref']

    def set_spatial_ref(self, kwargs):
        if not ('spatial_ref' in self):
            assert isinstance(kwargs, (dict, Spatial_ref, DataArray)), TypeError("spatial_ref must have type (dict, gspy.Spatial_ref)")
            if isinstance(kwargs, dict):
                crs = Spatial_ref.from_dict(kwargs)
            else:
                crs = kwargs # This is a pre-existing Spatial_ref/DataArray

            self['spatial_ref'] = crs
            self = self.assign_coords({'spatial_ref' : crs})

        return self

    def update_attrs(self, **kwargs):
        kwargs = flatten(kwargs, '', {})
        self.attrs.update(kwargs)

    # def _add_general_metadata_to_xarray(self, kwargs):
    #     kwargs = flatten(kwargs, '', {})
    #     self.attrs.update(kwargs)


        # if self.xarray['spatial_ref'].attrs['grid_mapping_name'] != 'latitude_longitude':
        #     self.xarray['x'].attrs['standard_name'] = 'projection_x_coordinate'
        #     self.xarray['y'].attrs['standard_name'] = 'projection_y_coordinate'
