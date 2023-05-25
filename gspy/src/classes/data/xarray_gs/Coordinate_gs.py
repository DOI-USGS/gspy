from numpy import arange
from .DataArray_gs import DataArray_gs

class Coordinate_gs(DataArray_gs):

    __slots__ = ()

    @classmethod
    def from_dict(cls, name, discrete=False, is_projected=False, **kwargs):
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

        kwargs['standard_name'] = cls.check_is_projected(name, is_projected)

        cls.check_standard_coordinates(name, **kwargs)

        # Add a check for units to conform to ARC reading
        if 'units' in kwargs:
            if kwargs['units'] == 'm':
                kwargs['units'] = 'meters'

        if not 'str' in [type(val) for val in centers]:
            kwargs['valid_range'] = cls.valid_range(centers, **kwargs)

        if discrete:
            self = cls(centers,
                    dims=[name],
                    attrs=kwargs)

        else:
            self = cls(centers,
                    dims=[name],
                    coords=kwargs.pop('coords', {name: centers}),
                    attrs=kwargs)

        return self

    @classmethod
    def from_values(cls, name, values, discrete=False, is_projected=False, **kwargs):

        kwargs['standard_name'] = cls.check_is_projected(name, is_projected)

        cls.check_standard_coordinates(name, **kwargs)
        
        return super(Coordinate_gs, cls).from_values(name, values, **kwargs)

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
            assert "axis" in kwargs, ValueError("coordinate definition for {} requires 'axis' defined. e.g. 'axis':'X' for x".format(name))
            if name == "z":
                assert "positive" in kwargs, ValueError("z coordinate definition requires entry 'positive' : 'up' or 'down'")
                assert "vertical_datum" in kwargs, ValueError("z coordinate definition requires entry 'vertical_datum', e.g. 'ground surface' ")
            if name == "t":
                assert "time_datum" in kwargs, ValueError("time coordinate definition requires entry for 'time_datum', e.g. 'Jan-01-1900'")