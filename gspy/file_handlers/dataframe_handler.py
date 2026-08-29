from .file_handler_abc import file_handler

class dataframe_handler(file_handler, key='dataframe'):
    """Handler for a table the caller has already read.

    For data that needed work before GSPy saw it, or that never came from a file
    GSPy can parse. Once constructed it is an ordinary handler, so everything
    downstream of :func:`gspy.file_handlers.open_datafile` is unchanged.

    >>> df = pd.read_csv('Resolve.csv')
    >>> df = df[df.line == 100200]                      # whatever the data needed
    >>> Tabular.read(df, metadata_file='Resolve_data_md.yml')

    A DataFrame carries no column descriptions, so unlike a format with a
    definition file there is nothing to glean here: the metadata is whatever the
    caller passes.

    """

    #: Claims no files. Reachable only by handing it a DataFrame.
    extensions = ()

    def __init__(self, df, metadata=None, name='dataframe', **kwargs):
        """Adopt a DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            Table to ingest. Columns that should become a second dimension need
            the same ``channel[0], channel[1], ...`` naming a file would use.
        metadata : dict, optional
            GSPy variable metadata, keyed by column name.
        name : str, optional
            Label used where a filename would be, e.g. in error messages and as
            the default name for a written metadata template.

        """
        super().__init__(name, metadata=metadata, df=df, **kwargs)

    @classmethod
    def can_read(cls, filename):
        """Never claims a file, so it cannot win format detection."""
        return False

    @property
    def columns(self):
        return self.df.columns

    @property
    def type(self):
        return 'dataframe'

    def read(self, metadata=None, df=None, **kwargs):
        """Take the DataFrame handed to ``__init__``. There is no file to read.

        Extra keyword arguments are accepted and ignored, so a call that already
        passes reader options or a system can hand over a DataFrame instead of a
        filename without being stripped down first.

        """
        self.df = df

        self.metadata = {}
        self.combine_metadata(metadata)

    def metadata_template(self, **kwargs):
        out = super().metadata_template(**kwargs)
        out['variables'] = self.variable_metadata_template(**kwargs)

        return out
