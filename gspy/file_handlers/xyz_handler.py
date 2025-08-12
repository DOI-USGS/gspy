from pprint import pprint
import re
import numpy as np
from pandas import read_csv, Series, concat
from .file_handler_abc import file_handler
from ..metadata.Metadata import Metadata

# class xyz_handler(file_handler):
#     stuff = None

class workbench_handler(file_handler):

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
        return 'xyz'

    @classmethod
    def read(cls, filename, metadata=None, **kwargs):

        assert 'system' in kwargs, ValueError("Need to pass a system through when reading workbench data")

        self = cls()

        self.filename = filename

        self.__read_xyz_data_files(metadata, **kwargs)

        return self

    def __read_xyz_data_files(self, metadata=None, **kwargs):
        self.metadata, n_header = self.__parse_xyz_metadata(self.filename)

        system = kwargs['system'].gs.get_system_with_method('electromagnetic')

        mapping = {i+1:c_label for i, c_label in enumerate(system.gs.component_labels)}

        self._df = self.read_xyz_data(self.filename, header=n_header, mapping=mapping)

        self.combine_metadata(metadata)

    def __parse_xyz_metadata(self, filename):

        metadata = dict()

        n_header = -1; done = False

        with open(filename, 'r') as file:
            while not done:
                n_header += 1
                line = file.readline()
                if 'Gates for channel' in line:
                    splt = line.split(':')
                    # metadata[f"channel {int(splt[0][-2])}"] = np.float64(splt[1][1:].split())
                if 'DUMMY' in line:
                    line = file.readline()
                    # metadata['dummy'] = np.float64(line[1:].strip('\n'))
                if 'DATE' in line:
                    n_header += 1
                    done = True

        return metadata, n_header

    def read_xyz_data(self, filename, **kwargs):

        mapping = kwargs.pop('mapping')

        df = read_csv(filename, sep=r',\s+', engine='python', **kwargs)
        df.columns = Series(df.columns.str.replace(r'[,/ ]+', '',regex=True))

        # define column groups
        unique_columns = ['DATE','TIME']
        base_columns = ['DATE','TIME','LINE_NO','UTMX','UTMY','ELEVATION']
        geometry_columns = ['RX_ALTITUDE',  'RX_ALTITUDE_STD',
                            'TX_ALTITUDE',  'TX_ALTITUDE_STD',
                            'TILT_X',  'TILT_X_STD',
                            'TILT_Y',  'TILT_Y_STD']

        # Create a base dataframe, starting with just bare coords, date, time, etc.
        # dfu = df.drop_duplicates(subset = unique_columns)[base_columns]
        # dfu = dfu.reset_index(drop=True)
        # n_duplicate = (df.shape[0] - dfu.shape[0]) / df.shape[0]

        # if n_duplicate != 0:
        #     print(f'There are {n_duplicate:.1%} lines with duplicate date-time')

        dfu = df[base_columns]

        df_dict = {}
        for key, value in mapping.items():
            # Filter the DataFrame for the current channel
            new_df = df[df['CHANNEL_NO'] == key]
            # new_df = new_df.drop(columns = ['CHANNEL_NO'])
            # new_df.reset_index(inplace=True)

            # # Merge with the original channel_df to get all columns
            # new_df = dfu.merge(channel_df, on=base_columns, how='left')

            # Fill missing rows with np.nan
            new_df = new_df.fillna(np.nan)

            # Only keep columns for relevant channel
            cols_to_drop = new_df.columns[new_df.columns.str.contains('DBDT') & ~new_df.columns.str.contains('Ch' + str(key))]
            new_df.drop(columns = cols_to_drop, inplace=True)

            renamer = {}
            for column in new_df.columns:
                if 'Ch' in column:
                    splt = column.split('GT')
                    new_name = f"{splt[0].replace(f'Ch{key}', value.upper())}_{np.int32(splt[1])-1}"

                    # new_name = column.replace(f"Ch{key}GT", "").replace(f'DBDT', value.upper())
                    renamer[column] = new_name
            new_df.rename(columns=renamer, inplace=True)

            # Store the DataFrame in the dictionary
            df_dict[value] = new_df
            # print(f'{channel_df.shape[0]} rows in channel {value} ({key}) vs {new_df.shape[0]} in combined dataset')

        df_geom = concat(df_dict.values())
        df_geom = df_geom[geometry_columns].groupby(level=0).mean()

        df_avg = concat([dfu, df_geom],axis=1)
        for key,df_i in df_dict.items():
            df_avg = concat([df_avg,df_i.filter(like='DBDT',axis=1)],axis=1)

        return df_avg




