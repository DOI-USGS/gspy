from abc import ABC, abstractmethod
from pandas import DataFrame
from pathlib import Path
from ..metadata.Metadata import Metadata

class file_handler(ABC):
    """Abstract base class to define file handlers

    Here a file handler reads in a file format into a DataFrame as self.df and metadata as a dict self.metadata.
    The DataFrame handles simple column names and values.  Columns that will be 2D need to have a header formatted as follows after reading
    channel[0] channel[1] ... channel[n].  GSpy will then combine those into a 2D xarray variable.
    If there is an accompnying metadata file that defines more information about columns, that should be read in
    as a dict with keys equal to the column names in the data file and values of dicts with any metadata from the file side.

    These metadata entries later get merged with the GSpy metadata when importing.
    """

    __slots__ = ()

    _allowed_file_types = ('aseg', 'csv', 'netcdf', 'loupe', 'xyz')

    def __init__(self):

        self._filename = None
        self._md_filename = None
        self._df = None
        self._metadata = None

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, value):
        assert isinstance(value, DataFrame), TypeError("df must have type pandas.DataFrame")
        self._df = value

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        assert isinstance(value, str), TypeError("filename must have type str")
        self._filename = value

    @property
    def md_filename(self):
        return self._md_filename

    @md_filename.setter
    def md_filename(self, value):
        assert isinstance(value, str), TypeError("filename must have type str")
        self._md_filename = value

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        assert isinstance(value, dict), TypeError('metadata must have type dict')
        self._metadata = value

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
    def read(self):
        """Read in datafiles and any accompanying metadata into a DataFrame and dict.

        Returns
        -------
        _type_
            _description_
        """
        return None

    def combine_metadata(self, new, **kwargs):
        self.metadata = Metadata.merge(self.metadata, new, **kwargs)

        # for key, item in self.metadata.items():
        #     assert all([x in item for x in ('long_name', 'standard_name', 'null_value', 'units')]), ValueError(f"Variable {key} Must have at least 'long_name', 'standard_name', 'null_value', 'units'")

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

    @abstractmethod
    def metadata_template(self, **kwargs):
        out = Metadata()

        template = {"content": "<summary statement of what the dataset contains>",
                    "comment": "<additional details or ancillary information>",
                    "type" : "??",
                    "method" : "??",
                    "submethod" : "??",
                    "instrument" : "??",
                    "structure" : "??",
                    "property" : "??",
                    }
        out["dataset_attrs"] = Metadata.merge(template, kwargs.get('dataset_attrs', {}))

        template = {"x" : "??",
                    "y" : "??",
                    "z" : "??",
                    "t" : "??"}
        out["coordinates"] = Metadata.merge(template, kwargs.get('coordinates', {}))

        if 'dimensions' in kwargs:
            template = {}
            out["dimensions"] = Metadata.merge(template, kwargs.get('dimensions', {}))

        return out


    def write_metadata_template(self, filename=None, **kwargs):
        if filename is None:
            filename = f"{Path(self.filename).stem}_metadata_template.yml"

        self.metadata_template(**kwargs).dump(filename)

        return f"Writing metadata to {filename}.\nEntries that need filling in are denoted with '??'"
