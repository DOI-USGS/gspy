import pandas as pd
from .file_handler_abc import file_handler

class csv_handler(file_handler, key='csv'):
    """CSV handler wrapping pandas

    The catch all: anything no other format claims is read as delimited text.

    """
    #: Lower than every other format, so a more specific handler always wins.
    priority = -1

    @classmethod
    def can_read(cls, filename):
        return True

    @property
    def columns(self):
        return self.df.columns

    def metadata_template(self, **kwargs):

        out = super().metadata_template(**kwargs)
        out['variables'] = self.variable_metadata_template(**kwargs)

        return out

    @property
    def type(self):
        return 'csv'

    def read(self, metadata=None, **kwargs):
        kwargs.pop('system', None)

        # Read the csv file
        self.df = pd.read_csv(self.filename, na_values=['NaN'], **kwargs)

        weird = (self.df.map(type) != self.df.iloc[0].apply(type)).any(axis=0)
        for w in weird.keys():
            if weird[w]:
                self.df[w] = pd.to_numeric(self.df[w], errors='coerce')

        self.metadata = {}
        self.combine_metadata(metadata)

    @classmethod
    def to_file(cls, tabular, filename):
        """Write a gspy Tabular out as a csv.

        A classmethod because writing needs no file to have been read.

        """
        tmpdf = tabular._obj.xr_to_dataframe()
        tmpdf.to_csv(filename, index=None)
