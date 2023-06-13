from copy import deepcopy
from numpy import arange, asarray, diff, isnan, median, nanmax, nanmin, r_, zeros, nan, min,max
from numpy import any as npany
from numpy import dtype as npdtype
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
        values = cls.catch_nan(values, name=name, **kwargs)

        if not isinstance(values[0], str):
            kwargs['valid_range'] = cls.valid_range(values, **kwargs)

        kwargs['grid_mapping'] = kwargs.pop('grid_mapping', 'spatial_ref')

        if 'dtype' in kwargs:
            values = values.astype(kwargs['dtype'])

        out = cls(values,
                dims=kwargs.pop('dimensions'),
                coords=kwargs.pop('coords'),
                attrs=kwargs)

        return out

    @staticmethod
    def catch_nan(values, name, **kwargs):

        if isinstance(values[0], str):
            return values

        nv = kwargs.get('null_value', 'not_defined')

        if nv == 'not_defined':
            assert not npany(isnan(values)), ValueError(("\nThere are NaNs or Empty values in data column {} and no defined null value in the json metadata file.\n"
                                                         "Define the 'null_value' for {} in the json file").format(name, name))
        else:
            values[isnan(values)] = nv
        return values

    @staticmethod
    def valid_range(values, **kwargs):
        nv = kwargs.get('null_value', 'not_defined')

        if nv == 'not_defined':
            return asarray([nanmin(values), nanmax(values)], dtype=kwargs.get('dtype', None))
        else:
            assert not isinstance(nv, str), ValueError("Numerical null_value defined as a string in json file for variable {}.  Please make it a number".format(kwargs['standard_name']))
            tmp = values[values != nv]
            return asarray([min(tmp), max(tmp)], dtype=kwargs.get('dtype', None))