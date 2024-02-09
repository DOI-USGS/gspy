import re
import numpy as np
import chardet
from pandas import read_csv, read_fwf, DataFrame


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

    @metadata.setter
    def metadata(self, value):
        assert isinstance(value, dict), TypeError('metadata must have type dict')
        self._metadata = value

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

    def col_widths_from_fortran_format(self, first):
        if first > 0:
            out = [first]
        else:
            out = []
        for key, value in self.metadata.items():
            fmt = value['format']
            if 'i' in fmt:
                width = fmt.split('i')
            elif 'f' in fmt:
                width = fmt.split('f')
            elif 'e'in fmt:
                width = fmt.split('e')
            elif 'es' in fmt:
                width = fmt.split('es')
            elif 'd' in fmt:
                width = fmt.split('d')
            elif 'g' in fmt:
                width = fmt.split('g')
            elif 'a' in fmt:
                width = fmt.split('a')

            if width[0] == '':
                width = np.int32(np.float32(width[-1]))
            else:
                width = np.int32(width[0]) * np.int32(np.float32(width[-1]))

            out.append(width)

        return out

    @classmethod
    def read(cls, data_file_name, fixed_format=False):
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
        first_col_width, self.metadata = self.parse_dfn_file(self.dfn_file_name)

        if fixed_format:
            widths = self.col_widths_from_fortran_format(first_col_width)

            test = read_fwf(self.data_file_name, widths=widths)

            if test.values.shape[1] != len(self.columns):
                test.columns = ['crap'] + self.columns
            else:
                test.columns = self.columns

            formats = self.numpy_formats
            tmp = DataFrame()
            for col in self.columns:
                tmp[col] = np.asarray(test[col], dtype=formats[col])

            self._df = tmp

        else:
            # Open the data file, there is no header
            self._df = read_csv(self.data_file_name, names=self.columns, dtype=self.numpy_formats, index_col=False, sep='\s+')

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
        lines = open(dfn_file_name, 'rb').readlines()

        first_col_width, dfn_md = self._parse_first_line(lines[0])

        for i, line in enumerate(lines[1:]):
            records = line.strip().split(b";")[1:]
            for record in records:
                if b"END DEFN" in record:
                    return first_col_width, dfn_md
                key, md = self._parse_record(record)
                dfn_md[key] = md

        return first_col_width, dfn_md

    def _parse_first_line(self, line):

        splits = line.strip().split(b';')

        first_col_width = 4
        dfn_md = {}
        for x in splits:
            if b":A" in x and b"COMMENT" not in x:
                first_col_width = np.int32(x.split(b":A")[1])

            if b"RT" not in x and b"COMMENT" not in x:
                key, md = self._parse_record(x)
                dfn_md[key] = md

        return first_col_width, dfn_md

    def _parse_record(self, line):

        assert not b";" in line, ValueError("Trying to parse {} with multiple semicolons")

        result = chardet.detect(line)
        assert result['encoding'] == "ascii", ValueError("Non ascii entry(its probably the units), on line \n{}".format(line))

        line = line.decode("utf-8")

        info = line.split(";")[-1]
        tmp = re.split(":|,", info)

        assert len(tmp) >= 2, ValueError("Could not parse a record name and format on line {}".format(line))

        standard_name, format = tmp[:2]
        if ' ' in standard_name:
            standard_name = standard_name.strip().replace(' ', '_')

        metadata = {'standard_name' : standard_name.strip().lower(),
                    'long_name' : "not_defined",
                    'units' : "not_defined",
                    'null_value' : "not_defined",
                    'format' : format.strip().lower()
                    }

        for attr in tmp[2:]:
            if 'NULL=' in attr or 'null=' in attr:
                metadata['null_value'] = re.split("=", attr)[-1]
                next

            if 'UNIT=' in attr or 'unit=' in attr or 'UNITS=' in attr or 'units=' in attr:
                metadata['units'] = re.split("=", attr)[-1]
                next

            if 'NAME=' in attr or 'name=' in attr:
                metadata['long_name'] = re.split("=", attr)[-1]
                next

        return standard_name, metadata
