from numpy import arange
from .DataArray_gs import DataArray_gs

import xarray as xr

@xr.register_dataarray_accessor("cordinate")
class Coordinate_gs(DataArray_gs):

    @classmethod
    def from_dict(cls, name, is_projected=False, is_dimension=False, **kwargs):
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
            values = kwargs.pop('centers')

        else:
            assert all([x in kwargs for x in ['origin', 'increment', 'length']]), ValueError("Explicit dimension definition {} must have 'origin', 'increment', 'length".format(name))
            x0, dx, nx = kwargs.pop('origin'), kwargs.pop('increment'), kwargs.pop('length')
            values = (arange(nx) * dx) + x0

        # Add a check for units to conform to ARC reading
        if 'units' in kwargs:
            if kwargs['units'] == 'm':
                kwargs['units'] = 'meters'

        return Coordinate_gs.from_values(name, values, is_projected, is_dimension, **kwargs)

    @classmethod
    def from_values(cls, name, values, is_projected=False, is_dimension=False, **kwargs):

        kwargs['standard_name'] = cls.check_is_projected(name, is_projected)

        cls.check_standard_coordinates(name, **kwargs)

        if is_dimension:
            dims = [name]
            coords = {name : values}
        else:
            dims = kwargs.pop('dimensions')
            coords = kwargs.pop('coords')

        return super().from_values(name, values, dimensions=dims, coords=coords, **kwargs)

    @staticmethod
    def check_is_projected(name, is_projected):
        out = name
        if is_projected:
            if name in ('x', 'y'):
                out = "projection_{}_coordinate".format(name)
        return out

    @staticmethod
    def check_standard_coordinates(name, **kwargs):
        if name in ("x", "y", "z", "t"):
            assert "axis" in kwargs, ValueError('coordinate definition for {} requires "axis" defined in the variable metadata. e.g. "axis":"X" for x'.format(name))
            if name == "z":
                assert "positive" in kwargs, ValueError('z coordinate definition requires entry "positive" : "up" or "down"')
                assert "vertical_datum" in kwargs, ValueError('z coordinate definition requires entry "vertical_datum", e.g. "ground surface"')
            if name == "t":
                assert "time_datum" in kwargs, ValueError('time coordinate definition requires entry for "time_datum", e.g. "Jan-01-1900"')