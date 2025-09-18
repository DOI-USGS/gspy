import re
from copy import copy
import numpy as np
import chardet
from os.path import isfile
from .csv_handler import csv_handler
from pandas import read_csv, read_fwf, DataFrame, concat, Series
from pprint import pprint


class loupe_handler(csv_handler):
    """Handler for Loupe data
    """


    @property
    def type(self):
        return 'loupe'

    @classmethod
    def read(cls, filename, metadata=None, **kwargs):
        """Read the contents of a Loupe data and desc file.

        First, we parse the definition file then use that with Pandas.

        Parameters
        ----------
        data_file_name : str
            Data file.

        Returns
        -------
        gspy.loupe_gs

        """
        self = cls()

        self.filename = filename

        self.md_filename = filename + ".desc"

        # Open the DFN and parse into a dict.
        desc_metadata = self.__parse_desc_file(self.md_filename)

        skiprows = self.__parse_header(self.filename)

        # Open the data file, there is no header
        df = read_csv(self.filename, index_col=False, sep=r'\s+', skiprows=skiprows)

        i_lines = np.squeeze(np.argwhere(['LINE' in x for x in df['FID'].values]))
        n_lines = i_lines.size
        line_length = np.diff(np.hstack([i_lines, len(df)])) - 2

        line_number = np.repeat(np.arange(n_lines)+1, line_length+1)

        i = np.squeeze(np.argwhere(['LINE' not in x for x in df['FID'].values]))
        df = df.iloc[i]

        n_records = len(df)
        components = [x for x in np.unique(df['C'])]

        del df['NCH']

        renamer = {}
        for col in df.columns:
            split = re.findall(r"[^\W\d]+|\d+", col)
            if len(split) > 1:
                renamer[col] = f"{split[0]}[{np.int32(split[1])-1}]"

        df.rename(columns=renamer, inplace=True)

        # Entries with only an index dim
        component_indices = [np.arange(0, n_records, np.size(components)),
                             np.arange(1, n_records, np.size(components)),
                             np.arange(2, n_records, np.size(components))]

        index = np.arange(np.size(component_indices[0]))
        line_number = line_number[component_indices[0]]

        out_df = {}
        for key in df:
            # Pull out measurements that are the same for each component
            if np.all(df[key].iloc[:3] == df[key].iloc[0]):
                out_df[key] = df[key].iloc[component_indices[0]].values
            else: # This is component wise data.
                for i, c in enumerate(components):
                    key_split = key.split('[')[0]

                    out_df[f"{c}_{key}"] = df[key].values[component_indices[i]]

                    if key_split in desc_metadata:
                        desc_metadata[f"{c}_{key_split}"] = copy(desc_metadata[key_split])
                        desc_metadata[f"{c}_{key_split}"]['standard_name'] = f"{c}_{key_split}".lower()

        out_df['line'] = line_number
        #TODO: Parse the units from the desc file too.

        self.df = DataFrame(out_df)

        self.metadata = metadata

        self.combine_metadata(desc_metadata, matched_keys=True)

        return self

    def __parse_desc_file(self, file_name):
        """Parses the ASEG GDF2 definition file but includes fixes.

        Parameters
        ----------
        dfn_file_name : str
            ASEG GDF2 definition file

        Returns
        -------
        dict

        """

        if not isfile(file_name):
            return {}

        lines = open(file_name, 'rb').readlines()

        desc_md = {}
        for i, line in enumerate(lines[1:]):
            s = line.split(b" ", 1)
            key = s[0].decode('utf-8')
            value = s[1].decode('utf-8').strip()

            if key[:2] == "CH":
                key = "CH"
            desc_md[key] = dict(
                            standard_name = key.lower(),
                            long_name = value
                        )

        return desc_md

    def __parse_header(self, filename):

        n_headers_lines = 0
        with open(filename, 'r') as f:
            for line in f:
                n_headers_lines += 1
                if 'LINE:' in line and n_headers_lines > 2:
                    break

        return n_headers_lines - 2
