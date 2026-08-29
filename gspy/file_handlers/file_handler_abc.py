from abc import ABC, abstractmethod
from inspect import isabstract
from pandas import DataFrame
from pathlib import Path
from ..metadata.Metadata import Metadata

#: Attributes the GS convention requires on every variable.
REQUIRED_VARIABLE_ATTRS = ('standard_name', 'long_name', 'units', 'missing_value')


class InsufficientMetadataError(Exception):
    """A data file could not be ingested because its metadata is incomplete.

    Carries the template that needs filling in, so a caller can decide what to do
    with it instead of parsing a message or hunting for a file written into the
    working directory.

    Attributes
    ----------
    template : gspy.Metadata
        A metadata skeleton for this file. Entries needing attention are marked
        with '??' or 'not_defined'. Write it out with ``template.dump(filename)``.
    filename : str
        The data file that could not be read.
    missing : tuple of str
        Dotted paths into the metadata that still need a human, e.g.
        ``('variables.alt', 'variables.line.units')``.

    """

    def __init__(self, template, filename, missing=()):
        self.template = template
        self.filename = str(filename)
        self.missing = tuple(missing)

        message = (f"Insufficient metadata to read {self.filename}.\n"
                   "Entries that need filling in are denoted with '??'.\n"
                   "The template is attached to this exception as .template, "
                   "dump it with template.dump('my_metadata.yml')")
        if self.missing:
            message += f"\nMissing: {', '.join(self.missing)}"

        super().__init__(message)


class file_handler(ABC):
    """Abstract base class to define file handlers

    Here a file handler reads in a file format into a DataFrame as self.df and metadata as a dict self.metadata.
    The DataFrame handles simple column names and values.  Columns that will be 2D need to have a header formatted as follows after reading
    channel[0] channel[1] ... channel[n].  GSpy will then combine those into a 2D xarray variable.
    If there is an accompnying metadata file that defines more information about columns, that should be read in
    as a dict with keys equal to the column names in the data file and values of dicts with any metadata from the file side.

    These metadata entries later get merged with the GSpy metadata when importing.

    Instantiating a handler reads the file, so ``handler.df`` is always valid.
    Use :func:`gspy.file_handlers.open_datafile` rather than a handler directly
    when the format should be detected from the file itself.

    Adding a new format
    -------------------
    Subclass this, pass a ``key`` that names the format, implement ``read``,
    ``columns``, ``type`` and ``metadata_template``, and declare which files the
    format claims::

        class my_handler(file_handler, key='mine'):
            extensions = ('.mine',)
            priority = 10

    Subclasses register themselves, so a new format needs no edit to the
    dispatcher. Abstract subclasses (a shared base with no ``read``) are skipped.

    """

    #: Every concrete subclass, keyed by its format name. Populated by __init_subclass__.
    _registry: dict[str, type] = {}

    #: Extensions this format claims, used by the default ``can_read``.
    extensions: tuple[str, ...] = ()

    #: Highest priority wins when more than one format claims a file.
    priority = 0

    def __init_subclass__(cls, key=None, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.key = key if key is not None else cls.__name__.removesuffix('_handler')

        if isabstract(cls):
            return

        if cls.key in file_handler._registry:
            raise ValueError(f"Two file handlers claim the key {cls.key!r}: "
                             f"{file_handler._registry[cls.key].__name__} and {cls.__name__}")

        file_handler._registry[cls.key] = cls

    def __init__(self, filename, metadata=None, **kwargs):
        """Read a data file and any metadata that comes with it.

        Parameters
        ----------
        filename : str or pathlib.Path
            Data file to read.
        metadata : dict, optional
            GSPy variable metadata to merge with whatever the file declares.

        """
        self._md_filename = None
        self._df = None
        self._metadata = {}
        self._file_metadata = {}

        self.filename = filename

        self.read(metadata=metadata, **kwargs)

    @classmethod
    def can_read(cls, filename):
        """Whether this handler recognises a file, on the strength of the file alone.

        Override when the format needs more than an extension, e.g. a sidecar
        definition file or a signature on the first line.

        Returns
        -------
        bool

        """
        return Path(filename).suffix.lower() in cls.extensions

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, value):
        if not isinstance(value, DataFrame):
            raise TypeError("df must have type pandas.DataFrame")
        self._df = value

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        if not isinstance(value, (str, Path)):
            raise TypeError("filename must have type str or pathlib.Path")
        self._filename = str(value)

    @property
    def md_filename(self):
        return self._md_filename

    @md_filename.setter
    def md_filename(self, value):
        if not isinstance(value, (str, Path)):
            raise TypeError("md_filename must have type str or pathlib.Path")
        self._md_filename = str(value)

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if not isinstance(value, dict):
            raise TypeError('metadata must have type dict')
        self._metadata = value

    @property
    def file_metadata(self):
        """Metadata the data file declared about itself, in GSPy metadata layout.

        Most formats describe their columns and nothing else, and return an empty
        dict. A format that defines a dimension, e.g. gate times in the header of
        a Workbench model file, returns it here as ``{'dimensions': {...}}`` for
        the caller to merge into the survey metadata.

        Returns
        -------
        dict

        """
        return self._file_metadata

    @property
    @abstractmethod
    def columns(self):
        return None

    @property
    @abstractmethod
    def type(self):
        """File type of the file handler

        Returns
        -------
        str
            File type
        """
        return None

    @property
    def nrecords(self):
        return self.df.shape[0]

    @abstractmethod
    def read(self, metadata=None, **kwargs):
        """Read the data file into self.df, and its metadata into self.metadata.

        Called by __init__, so a handler is read by the time it is returned.

        Parameters
        ----------
        metadata : dict, optional
            GSPy variable metadata to merge with whatever the file declares.

        """
        return None

    def combine_metadata(self, new, **kwargs):
        self.metadata = Metadata.merge(self.metadata, new or {}, **kwargs)

    @property
    def column_header_counts(self):
        """Takes the header of a csv and counts repeated entries

        A header "depth[0], depth[1], depth[2] will create an entry {'depth':3}

        Parameters
        ----------
        columns : list of str
            list of column names

        Returns
        -------
        dict
            Dictionary with each unique column name and its count

        """
        out = {}
        for col in self.columns:
            if '[' in col:
                col = col.split('[')[0]
            elif '_' in col:
                uparts = col.rsplit('_',-1)
                ubase = '_'.join(uparts[:-1])
                ulast = uparts[-1] if len(uparts) > 1 else ''
                if ulast.isdigit():
                    col = ubase
            if col in out:
                out[col] += 1
            else:
                out[col] = 1
        return out

    def missing_metadata(self, metadata=None):
        """Variable metadata a user still has to provide for this file.

        Reports rather than raises, so a caller can ask before committing to an
        ingest. Only covers the variables, since the handler cannot know what the
        survey needs of its dataset attributes or coordinates.

        Parameters
        ----------
        metadata : dict, optional
            The GSPy metadata to check, i.e. the contents of a metadata file.

        Returns
        -------
        tuple of str
            Dotted paths, e.g. ``('variables.alt', 'variables.line.units')``.
            Empty when nothing is missing.

        """
        metadata = Metadata(metadata or {})
        variables = metadata.get('variables', {})

        out = []
        for var in self.column_header_counts:
            if var not in variables:
                out.append(f"variables.{var}")
            else:
                out += [f"variables.{var}.{attr}" for attr in REQUIRED_VARIABLE_ATTRS
                        if attr not in variables[var]]

        out += [key for key, value in metadata.flatten().items()
                if isinstance(value, str) and '??' in value]

        return tuple(out)

    @abstractmethod
    def metadata_template(self, **kwargs):
        out = Metadata()

        template = {"content": "?? summary statement of what the dataset contains ??",
                    "comment": "?? additional details or ancillary information ??",
                    "type" : "?? data or models ??",
                    "method" : "?? what geophysical method(s) are represented by this dataset ??",
                    "mode" : "?? ground or airborne or borehole or ... ??",
                    "instrument" : "?? what is the instrument ??",
                    "structure" : "?? tabular or raster ??",
                    "property" : "?? is there a physical or geophysical property represented? ?",
                    }
        out["dataset_attrs"] = Metadata.merge(template, kwargs.get('dataset_attrs', {}))

        template = {"x" : "?? name of the x-axis coordinate variable ??",
                    "y" : "?? name of the y-axis coordinate variable ??",
                    "z" : "?? name of the z-axis (vertical) coordinate variable ??",
                    "t" : "?? name of the t-axis (temporal) coordinate variable ??"}
        out["coordinates"] = Metadata.merge(template, kwargs.get('coordinates', {}))

        template =  {'my_dimension_variable_name':
                                   {'standard_name': 'my_dimension_variable_name',
                                    'long_name': 'more descriptive name of this dimension variable, numbers below are examples for how a regular 1-D dimension can be auto-generated.',
                                    'units': 'units of the dimension',
                                    'missing_value': 'not_defined',
                                    'length': 10,
                                    'increment': 5.0,
                                    'origin': 2.5},
                    'my_other_dimension_variable_name':
                                   {'standard_name': 'my_other_dimension_variable_name',
                                    'long_name': 'A second example for how dimension variables can be defined. Again, numbers below are stand-ins for demonstration purposes. In this case the widths are irregular and might have overlapping bounds.',
                                    'units': 'units of the dimension',
                                    'missing_value': 'not_defined',
                                    'bounds': [[0,2],[2,6],[4,10],[8,16]],
                                    'centers': [1,4,7,12]}}

        out["dimensions"] = Metadata.merge(template, kwargs.get('dimensions', {}))

        return out

    def column_metadata(self, column):
        """What the data file itself declares about one of its columns.

        Empty unless the format describes its columns, e.g. an ASEG-GDF2 DFN file.

        Returns
        -------
        dict

        """
        return {}

    def variable_metadata_template(self, **kwargs):
        """A template entry for every column in the data file.

        Columns the file describes itself start from those descriptions, and
        anything the caller passes in ``variables`` wins over both.

        Returns
        -------
        dict

        """
        template = {"standard_name": "not_defined",
                    "long_name": "not_defined",
                    "missing_value": "not_defined",
                    "units": "not_defined"}

        existing = kwargs.get('variables', {})
        column_counts = self.column_header_counts

        out = {}
        for var in sorted(column_counts.keys()):
            tmp = Metadata.merge(template, self.column_metadata(var))
            tmp = Metadata.merge(tmp, existing.get(var, {}))
            if column_counts[var] > 1:
                tmp['dimensions'] = tmp.get('dimensions', ['index', '??'])
            out[var] = tmp

        return out

    def write_metadata_template(self, filename=None, **kwargs):
        """Write a metadata template for this file.

        Parameters
        ----------
        filename : str, optional
            Where to write. Defaults to '<data file stem>_metadata_template.yml'
            in the current directory.

        Returns
        -------
        pathlib.Path
            The file that was written.

        """
        if filename is None:
            filename = f"{Path(self.filename).stem}_metadata_template.yml"

        self.metadata_template(**kwargs).dump(str(filename))

        return Path(filename)
