import re
import numpy as np
from pandas import read_csv


class aseg_gdf2_gs(object):
    """Handler for aseg gdf2 files
    """

    @property
    def columns(self):
        out = []
        for key, value in self.metadata.items():
            test = re.split('es|e|f|i|g|d|a', value['format'])
            if test[0] != '':
                for i in range(np.int32(test[0])):
                    out.append('{}[{}]'.format(key, i))
            else:
                out.append(key)
        return out

    @property
    def data_file_name(self):
        return self._data_file_name

    @property
    def df(self):
        return self._df

    @property
    def metadata(self):
        return self._metadata

    @property
    def dfn_file_name(self):
        return self._dfn_file_name

    @property
    def nrecords(self):
        return self.df.shape[0]

    @property
    def numpy_formats(self):
        out = {}
        for key, value in self.metadata.items():
            fmt = value['format']
            if 'i' in fmt:
                npfmt = np.int32
            elif 'f' in fmt:
                npfmt = np.float64
            elif 'e'in fmt:
                npfmt = np.float64
            elif 'es' in fmt:
                npfmt = np.float64
            elif 'd' in fmt:
                npfmt = np.float64
            elif 'g' in fmt:
                npfmt = np.float64
            elif 'a' in fmt:
                npfmt = str
            out[key] = npfmt
        return out

    @classmethod
    def read(cls, data_file_name):
        """Read the contents of an ASEG-GDF2 file.

        First, we parse the definition file then use that with Pandas.

        Parameters
        ----------
        data_file_name : str
            Data file.

        Returns
        -------
        gspy.aseg_gdf_handler

        """
        self = cls()

        self._data_file_name = data_file_name
        self._dfn_file_name = data_file_name.split('.dat')[0] + ".dfn"

        # Open the DFN and parse into a dict.
        self._metadata = self.parse_dfn_file(self.dfn_file_name)

        # Open the data file, there is no header
        self._df = read_csv(self.data_file_name, names=self.columns, dtype=self.numpy_formats, index_col=False, delim_whitespace=True)

        return self

    def parse_dfn_file(self, dfn_file_name):
        """Parses the ASEG GDF2 definition file but includes fixes.

        Parameters
        ----------
        dfn_file_name : str
            ASEG GDF2 definition file

        Returns
        -------
        dict

        """
        lines = open(dfn_file_name, 'r').readlines()

        dfn_md = {}
        for line in lines[1:]:
            if "END DEFN" in line:
                line = line.replace(";END DEFN", "")

            info = line.split(";")[-1]
            tmp = info.split(":")

            if len(tmp) == 1:
                break

            standard_name, format = tmp[:2]

            if ' ' in standard_name:
                standard_name = standard_name.strip().replace(' ', '_')

            null_value = 'not_defined'
            if 'NULL' in info:
                null_value = re.split(':|,',info.split('NULL')[-1])[0].split('=')[1].strip()

            units = 'not_defined'
            if 'UNIT' in info:
                key = 'UNIT'
                if 'UNITS' in info:
                    key = 'UNITS'
                units = re.split(':|,',info.split(key)[-1])[0].split('=')[1].strip()

            long_name = 'not_defined'
            if 'NAME' in info:
                long_name = re.split(':|,',info.split('NAME')[-1])[0].split('=')[-1].strip()
            else:
                long_name = re.split(':|,', info)[-1].strip()

            dfn_md[standard_name] = {'standard_name' : standard_name.strip().lower(),
                                     'long_name' : long_name,
                                     'units' : units,
                                     'null_value' : null_value,
                                     'format' : format.strip().lower()
                                     }

        return dfn_md
