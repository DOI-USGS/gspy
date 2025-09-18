from pprint import pprint
import re
import numpy as np
from pandas import read_csv, Series, concat, Index
from .xyz_handler import xyz_handler
from ..metadata.Metadata import Metadata

class workbench_handler(xyz_handler):

    @classmethod
    def read(cls, filename, metadata=None, **kwargs):

        assert 'system' in kwargs, ValueError("Need to pass a system through when reading workbench data")

        self = cls()

        self.filename = filename

        self.__read(metadata, **kwargs)

        return self

    def __read(self, metadata=None, **kwargs):
        self.metadata, n_header = self.__parse_metadata(self.filename)

        system = kwargs['system'].gs.get_system_with_method('electromagnetic')

        mapping = {i+1:c_label for i, c_label in enumerate(system.gs.component_labels)}

        self._df = self.read_data(self.filename, header=n_header, mapping=mapping)

        self.combine_metadata(metadata)

    def __parse_metadata(self, filename):

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

    def read_data(self, filename, **kwargs):

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

        print(mapping)

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

class workbench_model_handler(xyz_handler):

    @classmethod
    def read(cls, filename, metadata=None, **kwargs):

        assert 'system' in kwargs, ValueError("Need to pass a system through when reading workbench data")

        self = cls()

        self.filename = filename

        self.__read(metadata, **kwargs)

        return self

    def __read(self, metadata=None, **kwargs):
        # self.metadata, n_header = self.__parse_metadata(self.filename)
        self.metadata = {}

        system = kwargs['system'].gs.get_system_with_method('electromagnetic')

        print(system)

        mapping = {i+1:c_label for i, c_label in enumerate(system.gs.component_labels)}

        self._df = self.read_data(self.filename, mapping=mapping)

        self.combine_metadata(metadata)

    def read_data(self, filename, **kwargs):

        mapping = kwargs.pop('mapping')

        ftypes = ['inv','dat','syn']

        for ft in ftypes: # read in syn/dat/inv files and parse header row and gate times
            file = f"{filename[:-8]}_{ft}.xyz"
            with open(file, 'r') as f:
                # gate_row = None
                for i, line in enumerate(f):
                    # if (ft == 'inv') & ('GATE TIMES' in line):
                    #     gate_row = i + 1
                    # if gate_row is not None:
                    #     if i == gate_row:
                    #         gates = np.float64(line.split()[1:])
                    if 'LINE_NO' in line:
                        header_row = i
                        break

            # put data into dataframe
            df = read_csv(file, header=header_row, sep=r"(?<!/)\s+", engine='python')
            df.columns = Series(df.columns.str.replace("/ ", ""))

            if ft == 'inv':
                df_combined = df

            elif (ft == 'dat') | (ft == 'syn'):

                if ft == 'dat':
                    # figure out which columns are which segment and whether dual moment or single
                    dat = df.filter(like='DATA_')
                    flg = dat.copy(deep=True)
                    flg[flg==9999] = 0
                    flg[flg>0] = 1
                    xprod = np.matmul(flg.T, flg).head(1)
                    #plt.pcolormesh(xprod)
                    colset1 = xprod.columns[xprod.any()]
                    colset2 = xprod.columns[~xprod.any()]

                    single_moment = np.array_equal(colset1, colset2)

                # iterate over mapping keys
                for segment, component in mapping.items():
                    if ft == 'dat':
                        prefix_dat = component + '_data_'
                        prefix_std = component + '_datastd_'
                    elif ft == 'syn':
                        prefix_dat = component + '_syn_'

                    # grab correct columns to merge
                    if single_moment:
                        component_data = df[df['SEGMENTS']==segment][colset1.insert(0,Index(['RECORD']))]
                        if ft == 'dat':
                            colset1std = colset1.str.replace('DATA','DATASTD')
                            component_std = df[df['SEGMENTS']==segment][colset1std.insert(0,Index(['RECORD']))]
                        colset=colset1
                    elif (segment == 1) | (segment == 3): #dual moment convention LM
                        component_data = df[df['SEGMENTS']==segment][colset1.insert(0,Index(['RECORD']))]
                        if ft == 'dat':
                            colset1std = colset1.str.replace('DATA','DATASTD')
                            component_std = df[df['SEGMENTS']==segment][colset1std.insert(0,Index(['RECORD']))]
                        colset=colset1
                    elif (segment == 2) | (segment == 4): #dual moment convention HM
                        component_data = df[df['SEGMENTS']==segment][colset2.insert(0,Index(['RECORD']))]
                        if ft == 'dat':
                            colset2std = colset2.str.replace('DATA','DATASTD')
                            component_std = df[df['SEGMENTS']==segment][colset2std.insert(0,Index(['RECORD']))]
                        colset=colset2

                    # merge into combined dataframe
                    for i, col in enumerate(colset):
                        datcol = f"{prefix_dat}{i+1}"
                        stdcol = f"{prefix_std}{i+1}"
                        df_combined = df_combined.merge(component_data[['RECORD',col]], how='left', on='RECORD')
                        df_combined = df_combined.rename(columns={col: datcol})
                        if ft == 'dat':
                            df_combined = df_combined.merge(component_std[['RECORD',col.replace('DATA','DATASTD')]], how='left', on='RECORD')
                            df_combined = df_combined.rename(columns={col.replace('DATA','DATASTD'): datcol.replace('data','datastd')})

        return df_combined