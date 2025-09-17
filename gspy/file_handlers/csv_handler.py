from copy import copy
from pathlib import Path
import pandas as pd
from ..metadata.Metadata import Metadata
from .file_handler_abc import file_handler

class csv_handler(file_handler):
    """CSV handler wrapping pandas

    """
    @property
    def columns(self):
        return self.df.columns

    def metadata_template(self, **kwargs):

        out = super().metadata_template(**kwargs)

        template = {"standard_name": "not_defined",
                    "long_name": "not_defined",
                    "null_value": "not_defined",
                    "units": "not_defined"}

        columns_counts = self.column_header_counts
        variables = {}
        columns = sorted(list(columns_counts.keys()))

        for var in columns:
            tmp = Metadata.merge(template, kwargs.get(var, {}))
            if columns_counts[var] > 1:
                tmp['dimensions'] = tmp.get('dimensions', ['index', '??'])
            variables[var] = tmp

        out['variables'] = variables

        return out

    @property
    def type(self):
        return 'csv'

    @classmethod
    def read(cls, filename, metadata=None, **kwargs):
        self = cls()

        self.filename = filename

        kwargs.pop('system', None)

        # Read the csv file
        self.df = pd.read_csv(filename, na_values=['NaN'], **kwargs)

        weird = (self.df.map(type) != self.df.iloc[0].apply(type)).any(axis=0)
        for w in weird.keys():
            if weird[w]:
                self.df[w] = pd.to_numeric(self.df[w], errors='coerce')

        self.metadata = {}
        self.combine_metadata(metadata)

        return self

    def to_file(self, xr_dataset, filename):

        tmpdf = xr_dataset.xr_to_dataframe()
        tmpdf.to_csv(filename, index=None)