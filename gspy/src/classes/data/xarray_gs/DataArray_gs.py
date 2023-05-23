from copy import deepcopy
from numpy import arange, asarray, diff, median, nanmax, nanmin, r_, zeros, nan
from xarray import DataArray

class DataArray_gs(DataArray):
    __slots__ = ()

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
        attrs['valid_range'] = cls.valid_range(bounds, **kwargs)

        dims = kwargs.pop('dims')
        coords = kwargs.pop('coords')

        self = cls(bounds,
                   dims=dims,
                   coords=coords,
                   attrs=attrs)

        return self

    @classmethod
    def from_values(cls, name, values, **kwargs):

        if 'dtype' in kwargs:
            values = values.astype(kwargs['dtype'])

        kwargs['valid_range'] = cls.valid_range(values, **kwargs)

        dims = kwargs.pop('dimensions')

        if 'coords' in kwargs:
        # coords = kwargs.pop('coords', None)
            out = cls(values,
                    dims=dims,
                    coords=kwargs.pop('coords'),
                    attrs=kwargs)
        else:
            out = cls(values,
                    dims=dims,
                    attrs=kwargs)

        return out

    @staticmethod
    def valid_range(values, **kwargs):

        nv = kwargs.get('null_value', 'not_defined')

        if nv == 'not_defined':
            return r_[nanmin(values), nanmax(values)]
        else:
            tmp = values.copy()
            tmp[tmp == nv] = nan
            return r_[nanmin(tmp), nanmax(tmp)]
