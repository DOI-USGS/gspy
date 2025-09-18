from numpy import arange
from .DataArray import DataArray
from ..metadata.Metadata import Metadata

class Coordinate(DataArray):
    """Accessor to xarray.DataArray to define a Coordinate.

    Checks necessary metadata to satisfy the CF convention, and allows use with GIS software.
    Handles both arbitrary coordinates and standard coordinates defined as x, y, z, or t used within NetCDF files.
    Standard coordinates have extra checks on the metadata.

    See Also
    --------
    Coordinate.from_dict : For instantiation
    Coordinate.from_values : For instantiation

    """
    @staticmethod
    def metadata_template(**kwargs):

        template = {"standard_name": "not_defined",
                    "long_name": "Can specify centers and/or bounds, or origin/increment/length",
                    "units": "not_defined",
                    "null_value": "not_defined",
                    "centers" : [0, 1, 2],
                    "bounds" : [[-0.5, 0.5], [0.5, 1.5], [1.5, 2.5]],
                    "origin" : -0.5,
                    "increment" : 1.0,
                    "length" : 3}

        return Metadata.merge(template, kwargs)


    @classmethod
    def from_dict(cls, name, is_projected=False, is_dimension=False, **kwargs):
        """Specifically generates a coordinate/dimension from a dict.

        Automatically checks/generates required Coordinate metadata and bounds. If the coordinate is a "standard coordinate" i.e. ('x', 'y', 'z', 't'), extra checks on metadata are performed.

        Parameters
        ----------
        name : str
            The name of the coordinate to attach
        is_projected : bool
            If the coordinate is projected, the standard_name metadata entry needs to change
        is_dimension : bool
            If the coordinate is a coordinate-dimension defines its dims as itself

        Other Parameters
        ----------------
        centers : array_like, optional
            * Explicit definition of Coordinate center values. Used for non-uniformly distanced center values.
            * Has shape (size of dimension, ) defining the center values of each "cell"
        increment : scalar, optional
            Increment of the Coordinate centers. Only used if centers is None.
        length : int, optional
            Size of the Coordinate centers. Only used if centers is None.
        origin : scalar, optional
            Lower limit of the Coordinate centers. Only used if centers is None.

        See Also
        --------
        .DataArray.DataArray.from_values : For GS standard metadata keywords
        Coordinate.check_standard_coordinates : For extra keywords when name in ('x', 'y', 'z', 't')

        Example
        -------
        >>> depth_dict = {"standard_name": "depth",
        >>>               "long_name": "Depth below earth's surface DTM",
        >>>               "units": "m",
        >>>               "null_value": "not_defined",
        >>>               "centers" : [2.5, 7.5, 20.0]}
        >>> Coordinate.from_dict('depth', **depth_dict)

        """
        values = kwargs.pop('values', kwargs.pop('centers', None))

        if values is None:
            # 'origin', 'increment',
            assert all([x in kwargs for x in ['length']]), ValueError(f"Explicit dimension definition {name} must have at least length, optionally origin and increment")
            x0, dx, nx = kwargs.pop('origin', 0), kwargs.pop('increment', 1), kwargs.pop('length')
            values = (arange(nx) * dx) + x0

        kwargs['values'] = values

        # Add a check for units to conform to ARC reading
        if 'units' in kwargs:
            if kwargs['units'] == 'm':
                kwargs['units'] = 'meters'

        return Coordinate.from_values(name, is_projected, is_dimension, **kwargs)

    @classmethod
    def from_values(cls, name, is_projected=False, is_dimension=False, **kwargs):
        """Generate a Coordinate from an array of values.

        Parameters
        ----------
        name : str
            The name of the coordinate to attach
        is_projected : bool
            If the coordinate is projected, the standard_name metadata entry needs to change
        is_dimension : bool
            If the coordinate is a coordinate-dimension defines its dims as itself.

        Other Parameters
        ----------------
        centers : array_like, optional
            Explicit definition of Coordinate center values. Used for non-uniformly distanced center values.
            Has shape (size of dimension, ) defining the center values of each "cell"
        increment : scalar, optional
            Increment of the Coordinate centers. Only used if centers is None.
        length : int, optional
            Size of the Coordinate centers. Only used if centers is None.
        origin : scalar, optional
            Lower limit of the Coordinate centers. Only used if centers is None.

        See Also
        --------
        .DataArray.DataArray.from_values : For GS convention metadata keywords
        Coordinate.check_standard_coordinates : For extra keywords when creating a standard coordinate

        Example
        -------
        >>> depth_dict = {"standard_name": "depth",
        >>>               "long_name": "Depth below earth's surface DTM",
        >>>               "units": "m",
        >>>               "null_value": "not_defined",
        >>>               "centers" : [2.5, 7.5, 20.0]}
        >>> Coordinate.from_dict('depth', np.r_[2.5, 7.5, 20.0], **depth_dict)

        """
        kwargs['standard_name'] = cls.check_is_projected(name, is_projected)

        cls.check_standard_coordinates(name, **kwargs)

        if is_dimension:
            dims = [name]
            coords = {name : kwargs['values']}
        else:
            dims = kwargs.pop('dimensions')
            coords = kwargs.pop('coords')

        if "axis" in kwargs:
            kwargs["axis"] = kwargs["axis"].upper()

        return super().from_values(name, dimensions=dims, coords=coords, **kwargs)

    @staticmethod
    def check_is_projected(name, is_projected):
        """Checks for a projected standard coordinate x or y

        Parameters
        ----------
        name : str
            Name of the coordinate
        is_projected : bool
            Is the coordinate projected or not

        Returns
        -------
        out : str

        """
        out = name
        if is_projected:
            if name in ('x', 'y'):
                out = f"projection_{name}_coordinate"
        return out

    @staticmethod
    def check_standard_coordinates(name, **kwargs):
        """If this is a standard coordinate do some extra checks on metadata.

        Parameters
        ----------
        axis : int, optional
            Axis this Coordinate belongs to .
        positive : str, optional
            "up" or "down". Only used if name == 'z'.
        datum : str, optional
            Datum. Only used if name == 'z' or 't'.

        """
        if name in ("x", "y", "z", "t"):
            if 'axis' not in kwargs:
                kwargs['axis'] = name.upper()
            if name == "z":
                assert all([x in kwargs for x in ["positive", "datum"]]), ValueError("z coordinate definition requires entries positive: up or down, and datum: ground surface ")
            if name == "t":
                assert "datum" in kwargs, ValueError("time coordinate definition requires datum entry e.g. datum: Jan-01-1900")