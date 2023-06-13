from copy import deepcopy
from pprint import pprint
from numpy import all, arange, asarray, diff, median, r_, zeros
from xarray import DataArray, Dataset, load_dataset
from .DataArray_gs import DataArray_gs
from .Coordinate_gs import Coordinate_gs

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
        # Add the actual coordinate values
        self[name] = Coordinate_gs.from_dict(name, self.is_projected, is_dimension=is_dimension, **kwargs)

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
            kwargs['coords'] = kwargs.pop('coords', {key:self[key] for key in kwargs['dimensions']})

        self[name] = Coordinate_gs.from_values(name, values, is_dimension=is_dimension, **kwargs)
        self = self.assign_coords({name : self[name]})

        # Add the bounds of the coordinate
        if not discrete:
            self = self.add_bounds_to_coordinate(name, **bounding_dict)

        return self

    def add_variable_from_values(self, name, values, **kwargs):
        assert all(values.shape == tuple([self[vdim].size for vdim in kwargs['dimensions']])), ValueError("Shape {} of variable {} does not match specified dimensions with shape {}".format(values.shape, name, kwargs['dimensions']))

        kwargs['coords'] = [self.coords[dim] for dim in kwargs['dimensions']]
        self[name] = DataArray_gs.from_values(name, values, **kwargs)

    def add_bounds_to_coordinate(self, name, **kwargs):

        # The bounds are 2xN and need their own "nv" dimension
        self = self._add_nv()

        # Now add the bound
        self[name + '_bnds'] = DataArray_gs.add_bounds_to_coordinate_dimension(self[name],
                                                                               name,
                                                                               dims = (*[dim for dim in self[name].dims], 'nv'),
                                                                               coords=(*[self[dim] for dim in self[name].dims], self['nv']),
                                                                               **kwargs)
        self[name].attrs['bounds'] = name + '_bnds'

        return self

    def _add_nv(self):
        if not 'nv' in self:
            self = self.add_coordinate_from_values('nv',
                                                   r_[0, 1],
                                                   is_projected=False,
                                                   is_dimension=True,
                                                   discrete=True,
                                                   **dict(standard_name = 'number_of_vertices',
                                                          long_name = 'Number of vertices for bounding variables',
                                                          units = 'not_defined',
                                                          null_value = 'not_defined'))
        return self

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
