from os.path import isfile
from pprint import pprint
import re
import numpy as np
from pandas import read_csv, Series, concat
from .file_handler_abc import file_handler
from ..metadata.Metadata import Metadata

class xyz_handler(file_handler):

    @property
    def columns(self):
        return self.df.columns

    @property
    def type(self):
        return 'xyz'

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

    @staticmethod
    def is_workbench(filename):
        with open(filename, 'r') as f:
            line = f.readline()
        return '/INFO' in line

    @staticmethod
    def is_workbench_model(filename):
        return isfile(filename[:-7]+"dat.xyz") & isfile(filename[:-7]+"inv.xyz") & isfile(filename[:-7]+"syn.xyz")





