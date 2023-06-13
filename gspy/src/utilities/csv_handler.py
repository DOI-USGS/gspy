import pandas as pd

class csv_gs(object):

    @property
    def columns(self):
        return self.df.columns

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
                npfmt = np.float32
            elif 'e'in fmt:
                npfmt = np.float64
            elif 'es' in fmt:
                npfmt = np.float64
            elif 'd' in fmt:
                npfmt = np.float64
            elif 'g' in fmt:
                npfmt = np.float64
            out[key] = npfmt
        return out

    @classmethod
    def read(cls, filename):

        self = cls()
        # Read the csv file
        self._df = pd.read_csv(filename, na_values=['NaN'])
        # print(file['line'][1876])
        weird = (self.df.applymap(type) != self.df.iloc[0].apply(type)).any(axis=0)
        for w in weird.keys():
            if weird[w]:
                self.df[w] = pd.to_numeric(self.df[w], errors='coerce')

        return self