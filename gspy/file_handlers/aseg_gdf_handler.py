import re
import numpy as np
import chardet
from pandas import read_csv, read_fwf, DataFrame
from .file_handler_abc import file_handler
from ..metadata.Metadata import Metadata


class aseg_gdf2_handler(file_handler):
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

    def metadata_template(self, **kwargs):

        out = super().metadata_template

        coords = self.metadata['coordinates']
        if 'x' in coords:
            out[coords['x']] = {"axis" : "X"}
        if 'y' in coords:
            out[coords['y']] = {"axis" : "Y"}
        if 'z' in coords:
            out[coords['z']] = {"axis" : "Z",
                                    "positive" : "up or down?",
                                    "datum" : "not_defined"}
        if 't' in coords:
            out[coords['t']] = {"axis" : "T",
                                    "datum" : "not_defined"}

        return out

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

    @property
    def type(self):
        return 'aseg'

    def __col_widths_from_fortran_format(self, first):
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
    def read(cls, filename, metadata=None, fixed_format=False, **kwargs):
        """Read the contents of an ASEG-GDF2 file.

        First, we parse the definition file then use that with Pandas.

        Parameters
        ----------
        filename : str
            Data file.

        Returns
        -------
        gspy.aseg_gdf_handler

        """
        self = cls()

        self.filename = filename
        self.md_filename = filename.split('.dat')[0] + ".dfn"

        # Open the DFN and parse into a dict.
        first_col_width, self.metadata = self.__parse_dfn_file(self.md_filename)

        if fixed_format:
            widths = self.__col_widths_from_fortran_format(first_col_width)

            test = read_fwf(self.filename, widths=widths)

            if test.values.shape[1] != len(self.columns):
                test.columns = ['-'] + self.columns
            else:
                test.columns = self.columns

            formats = self.numpy_formats
            tmp = DataFrame()
            for col in self.columns:
                tmp[col] = np.asarray(test[col], dtype=formats[col])

            self._df = tmp

        else:
            # Open the data file, there is no header
            self._df = read_csv(self.filename, names=self.columns, dtype=self.numpy_formats, index_col=False, sep=r'\s+')

        self.combine_metadata(metadata)

        return self

    def __parse_dfn_file(self, filename):
        """Parses the ASEG GDF2 definition file but includes fixes.

        Parameters
        ----------
        filename : str
            ASEG GDF2 definition file

        Returns
        -------
        dict

        """
        lines = open(filename, 'rb').readlines()

        first_col_width, dfn_md = self.__parse_first_line(lines[0])

        for i, line in enumerate(lines[1:]):
            records = line.strip().split(b";")[1:]
            for record in records:
                if b"END DEFN" in record:
                    return first_col_width, dfn_md
                key, md = self.__parse_record(record)
                dfn_md[key] = md

        return first_col_width, dfn_md

    def __parse_first_line(self, line):

        splits = line.strip().split(b';')

        first_col_width = 4
        dfn_md = {}
        for x in splits:
            if b":A" in x and b"COMMENT" not in x:
                first_col_width = np.int32(x.split(b":A")[1])

            if b"RT" not in x and b"COMMENT" not in x:
                key, md = self.__parse_record(x)
                dfn_md[key] = md

        return first_col_width, dfn_md

    def __parse_record(self, line):
        """Parse a single line in the aseg DFN file

        Parameters
        ----------
        line : str
            line in file

        Returns
        -------
        standard_name : str
            Key name for the record
        metadata : dict
            Metadata for this key name

        """
        assert not b";" in line, ValueError("Trying to parse {} with multiple semicolons")

        # Double check for non-ascii entries and Error out
        result = chardet.detect(line)
        assert result['encoding'] == "ascii", ValueError("Non ascii entry(its probably the units), on line \n{}".format(line))

        # Decode the line in the DFN to utf-8
        line = line.decode("utf-8")

        # Split the line based on semi colons
        # And then again using : or ,
        info = line.split(";")[-1]
        tmp = re.split(":|,", info)

        assert len(tmp) >= 2, ValueError("Could not parse a record name and format on line {}".format(line))

        # The first two entries in the record are std_name and entry format
        standard_name, format = tmp[:2]
        if ' ' in standard_name:
            standard_name = standard_name.strip().replace(' ', '_')

        # Create a template
        metadata = {'standard_name' : standard_name.strip().lower(),
                    'long_name' : "not_defined",
                    'units' : "not_defined",
                    'null_value' : "not_defined",
                    'format' : format.strip().lower()
                    }

        for attr in tmp[2:]:
            # For each entry in the record parse potentially different substrings for "name", or "units".
            attr = attr.strip()
            attr = attr.replace(" =", "=")

            converter = np.int32 if 'i' in format else np.float64

            if 'NULL=' in attr or 'null=' in attr:
                attr = attr.replace(" ", "")
                metadata['null_value'] = converter(re.split("=", attr)[-1])

            elif 'UNIT=' in attr or 'unit=' in attr or 'UNITS=' in attr or 'units=' in attr:
                attr = attr.replace(" ", "")
                metadata['units'] = re.split("=", attr)[-1]

            elif 'NAME=' in attr or 'name=' in attr:
                metadata['long_name'] = re.split("=", attr)[-1]

            else: # This should be the long name
                metadata['long_name'] = attr

        return standard_name, metadata

    @staticmethod
    def _create_variable_metadata_template(filename, *args, **kwargs):
        """Generates a template metadata file for variables only.

        Assumes metadata has been provided for the dataset already, but creates extra entries for variables.

        """
        tmp_dic = {}
        coords = kwargs['coordinates']
        if 'x' in coords:
            tmp_dic[coords['x']] = {"axis" : "X"}
        if 'y' in coords:
            tmp_dic[coords['y']] = {"axis" : "Y"}
        if 'z' in coords:
            tmp_dic[coords['z']] = {"axis" : "Z",
                                    "positive" : "up or down?",
                                    "datum" : "not_defined"}
        if 't' in coords:
            tmp_dic[coords['t']] = {"axis" : "T",
                                    "datum" : "not_defined"}

        template_filename = "{}_variable_metadata_template.{}".format(*filename.split(os.sep)[-1].split('.'))

        dump_metadata_to_file({'variable_metadata':tmp_dic}, template_filename)

        s = ("\nGspy requires additional metadata on top of the ASEG standard in order to honour the CF convention.\n"
             "We are creating a template file called {} that you need to fill out.\n"
             "Once filled out, add that 'variable_metadata' dictionary to the metadata file\n").format(template_filename)

        raise Exception(s)


    def to_file(self, xr_dataset, filename, default_f32="f10.3", default_f64="g12.6"):

        skip_these = [xr_dataset.coords[x].attrs['bounds'] for x in xr_dataset.dims if 'bounds' in xr_dataset.coords[x].attrs]

        row = 0
        with open(filename, 'w') as f:
            f.write("DEFN   ST=RECD,RT=COMM;RT:A4;COMMENTS:A80\n")
            for i, key in enumerate(xr_dataset.data_vars):

                if key in skip_these:
                    continue

                var = xr_dataset[key]
                attrs = var.attrs

                # Grab the null value
                null = ""
                if attrs['null_value'] != "not_defined":
                    null = "NULL={},".format(attrs['null_value'])
                # Grab the units
                units = ""
                if 'units' in attrs:
                    if attrs['units'] != "not_defined":
                        units = "UNITS={},".format(attrs['units'])
                    # Grab the format if present, otherwise use a default

                fformat = attrs.get('format', self.get_fortran_format(key, default_f32=default_f32, default_f64=default_f64))

                strng = "DEFN {} ST=RECD,RT=;{}:{}:{}{}NAME={}\n".format(row, var.attrs['standard_name'], fformat, null, units, attrs['long_name'])
                f.write(strng)

                row += 1
            f.write("DEFN {} ST=RECD,RT=;END DEFN\n".format(row))
        """Export tabular data to an ASEG formatted data file

        Parameters
        ----------
        filename : str
            Path to output aseg file

        """
        raise NotImplementedError("Cannot yet write to aseg")