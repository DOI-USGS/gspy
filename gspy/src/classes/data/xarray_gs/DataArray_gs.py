from copy import deepcopy
from numpy import arange, asarray, diff, median, nanmax, nanmin, r_, zeros, nan
from xarray import DataArray

class DataArray_gs(DataArray):
    __slots__ = ()

    @classmethod
    def coordinate_from_dict(cls, name, discrete=False, is_projected=False, **kwargs):
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
        if 'centers' in kwargs:
            centers = kwargs.pop('centers')

        else:
            assert all([x in kwargs for x in ['origin', 'increment', 'length']]), ValueError("Explicit dimension definition {} must have 'origin', 'increment', 'length".format(name))
            x0, dx, nx = kwargs.pop('origin'), kwargs.pop('increment'), kwargs.pop('length')
            centers = (arange(nx) * dx) + x0

        coords = None if discrete else {name: centers}

        if is_projected:
            if name in ('x', 'y'):
                kwargs['standard_name'] = "projection_{}_coordinate".format(name)

        # Add a check for units to conform to ARC reading
        if 'units' in kwargs:
            if kwargs['units'] == 'm':
                kwargs['units'] = 'meters'
        
        # valid range
        if kwargs['null_value'] != 'not_defined':
            maskvalues = deepcopy(centers)
            maskvalues[maskvalues == kwargs['null_value']] = nan
            kwargs['valid_range'] = [nanmin(maskvalues), nanmax(maskvalues)]
        else:
            kwargs['valid_range'] = [nanmin(centers), nanmax(centers)]

        self = cls(
                   centers,
                   dims=[name],
                   coords=coords,
                   attrs=kwargs)

        return self

    @classmethod
    def add_bounds_to_coordinate_dimension(cls, coordinate, name, bounds=None, **kwargs):
        """For an existing coordinate, compute its bounds and attach.

        Parameters
        ----------
        bounds : array_like, optional
            if not present, bounds are computed. Otherwise assign them.

        """
        # Return if the coordinate already has bounds
        if 'bounds' in coordinate.attrs:
            return
        if bounds is None:
            bounds = zeros((coordinate.size, 2))
            centre = median(diff(coordinate.values)) * 0.5
            bounds[:, 0] = coordinate.values - centre
            bounds[:, 1] = coordinate.values + centre
        else:
            bounds = asarray(bounds)
            centers = coordinate.values
            if bounds.shape == (centers.size+1, ):
                bounds = asarray((bounds[:-1], bounds[1:])).transpose()
            else:
                assert bounds.shape == (centers.size, 2), ValueError('size of coordinate bounds must be 2D array size of centers, or +1 list size of centers that can be reshaped')

        attrs = coordinate.attrs.copy()
        attrs['standard_name'] = coordinate.attrs['standard_name'] + '_bounds'
        attrs['long_name'] = coordinate.attrs['long_name'] + ' cell boundaries'
        if attrs['null_value'] != 'not_defined':
            maskvalues = deepcopy(bounds)
            maskvalues[maskvalues == kwargs['null_value']] = nan
            attrs['valid_range'] = [nanmin(maskvalues), nanmax(maskvalues)]
        else:
            attrs['valid_range'] = [nanmin(bounds), nanmax(bounds)]
        
        self = DataArray(bounds,
                         dims=[name, 'nv'],
                         coords={name: coordinate, 'nv': r_[0, 1]},
                         attrs=attrs)
        
        #self.attrs['bounds'] = name + '_bnds'
        return self

    @classmethod
    def from_values(cls, name, values, **kwargs):

        if 'dtype' in kwargs:
            values = values.astype(kwargs['dtype'])

        kwargs['valid_range'] = cls.valid_range(values, **kwargs)

        dims = kwargs.pop('dimensions')
        coords = kwargs.pop('coords', None)
        
        out = cls(values,
                   dims=dims,
                   coords=coords,
                   attrs=kwargs)

        return out
    
    @staticmethod
    def valid_range(values, **kwargs):

        if kwargs['null_value'] == 'not_defined':
            return r_[nanmin(values), nanmax(values)]
        else:
            mask = values != kwargs['null_value']
            return r_[nanmin(values, where=mask), nanmax(values, where=mask)] 
