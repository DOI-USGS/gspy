import numpy as np
from pandas import read_csv, Series, concat
from .xyz_handler import xyz_handler

class _workbench_names:
    """Column naming shared by the Workbench exports."""

    #: Newer Workbench versions export UTMX and UTMY as X and Y.
    _alternatives = {'X': 'UTMX', 'Y': 'UTMY', 'UTMX': 'X', 'UTMY': 'Y'}

    @classmethod
    def aliases(cls, name):
        return [name] + ([cls._alternatives[name]] if name in cls._alternatives else [])

    @staticmethod
    def _tidied(columns):
        """ALTITUDE_[m] is ALTITUDE, and RHO_STD1 is RHO_STD_1. A numbered bracket,
        RHO[1], is left alone."""
        columns = columns.str.replace(r'_\[\D[^\]]*\]$', '', regex=True)
        return columns.str.replace(r'_STD(\d+)$', r'_STD_\1', regex=True)

class workbench_handler(_workbench_names, xyz_handler, key='workbench'):
    """Handler for Aarhus Workbench .xyz data
    """
    priority = 10

    @classmethod
    def can_read(cls, filename):
        return super().can_read(filename) and cls.is_workbench(filename)

    def read(self, metadata=None, system=None, **kwargs):
        """Read a Workbench .xyz data file.

        Parameters
        ----------
        metadata : dict, optional
            GSPy variable metadata.
        system : xarray.DataTree
            The system this data was collected with. Its couplet labels name the
            channels in the file, so the read cannot proceed without it.

        """
        if system is None:
            raise ValueError(f"Need to pass a system through when reading workbench data {self.filename}")

        self.metadata, n_header = self.__parse_metadata(self.filename)

        system = system.gs.get_system_with_method('electromagnetic')

        mapping = {i+1:c_label for i, c_label in enumerate(system.gs.couplet_labels)}

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
                    # key = splt[0].removeprefix('/').strip().replace(" ", "_")
                    # metadata[key] = np.float64(splt[1].split())
                    # print(metadata[key].size)

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
        df.columns = self._tidied(Series(df.columns.str.replace(r'[,/ ]+', '',regex=True)))

        # define column groups
        unique_columns = ['DATE','TIME']
        base_columns = [next((name for name in self.aliases(column) if name in df.columns), column)
                        for column in ['DATE','TIME','LINE_NO','UTMX','UTMY','ELEVATION']]
        geometry_columns = ['RX_ALTITUDE',  'RX_ALTITUDE_STD',
                            'TX_ALTITUDE',  'TX_ALTITUDE_STD',
                            'TILT_X',  'TILT_X_STD',
                            'TILT_Y',  'TILT_Y_STD']

        # Create a base dataframe, starting with just bare coords, date, time, etc.
        # dfu = df.drop_duplicates(subset = unique_columns)[base_columns]
        # dfu = dfu.reset_index(drop=True)
        # n_duplicate = (df.shape[0] - dfu.shape[0]) / df.shape[0]

        # if n_duplicate != 0:
        #     print(f"There are {n_duplicate:.1%} lines with duplicate date-time")

        dfu = df[base_columns]

        df_dict = {}
        geometry = {}
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

            # DBDT_Ch1GT5 is gate 4 of the first couplet, LM_Z_DBDT_4, and DBDT_STD_Ch1GT5 is LM_Z_DBDT_STD_4
            renamer = {}
            for column in new_df.columns:
                if 'Ch' in column:
                    splt = column.split('GT')
                    std = '_STD' if '_STD_' in splt[0] else ''
                    renamer[column] = f"{value.upper()}{std}_{np.int32(splt[1])-1}"
            new_df.rename(columns=renamer, inplace=True)

            # Store the DataFrame in the dictionary
            df_dict[value] = new_df[list(renamer.values())]
            geometry[value] = new_df[geometry_columns]
            # print(f'{channel_df.shape[0]} rows in channel {value} ({key}) vs {new_df.shape[0]} in combined dataset')

        df_geom = concat(geometry.values())
        df_geom = df_geom.groupby(level=0).mean()

        df_avg = concat([dfu, df_geom, *df_dict.values()],axis=1)

        return df_avg

class workbench_model_handler(_workbench_names, xyz_handler, key='workbench_model'):
    """Handler for Aarhus Workbench .xyz inverted models

    A model .xyz comes as a set of three: _dat, _inv and _syn. The gate times in
    their headers define a dimension, returned in ``file_metadata``. A multi-node
    export writes no gate times, so the system yml has to define them.

    """
    #: Beats workbench_handler, which claims any .xyz Workbench file.
    priority = 20

    @classmethod
    def can_read(cls, filename):
        return super().can_read(filename) and cls.is_workbench_model(str(filename))

    def read(self, metadata=None, system=None, **kwargs):
        """Read a Workbench .xyz model file and its siblings.

        Parameters
        ----------
        metadata : dict, optional
            GSPy variable metadata.
        system : xarray.DataTree
            The system this data was collected with. Its couplet labels name the
            channels in the files, so the read cannot proceed without it.

        """
        if system is None:
            raise ValueError(f"Need to pass a system through when reading workbench data {self.filename}")

        self.metadata = {}

        system = system.gs.get_system_with_method('electromagnetic')

        mapping = {i+1:c_label for i, c_label in enumerate(system.gs.couplet_labels)}

        self._df, self._file_metadata = self.read_data(self.filename, mapping=mapping)

        if 'dimensions' not in self._file_metadata and 'couplet_gate_times' not in system:
            raise ValueError(f"{self.filename} does not list its gate times, as a multi-node export does not. "
                             "Define the gate times dimensions in the system yml, and name them with the couplet's gate_times.")

        self.combine_metadata(metadata)

    def read_data(self, filename, **kwargs):

        mapping = kwargs.pop('mapping')

        ftypes = ['inv','dat','syn']

        gate_times = None
        for ft in ftypes: # read in syn/dat/inv files and parse header row and gate times
            file = f"{filename[:-8]}_{ft}.xyz"
            with open(file, 'r') as f:
                # gate_row = None
                i = 0
                while (line := f.readline()):
                    # if (ft == 'inv') & ('GATE TIMES' in line):
                    #     gate_row = i + 1
                    if 'GATE TIMES' in line:
                        nl = f.readline()
                        i += 1
                        gate_times = np.float64(nl.removeprefix('/').split())

                    if 'LINE_NO' in line:
                        header_row = i
                        break
                    i += 1

            # put data into dataframe
            df = read_csv(file, header=header_row, sep=r"(?<!/)\s+", engine='python')
            df.columns = self._tidied(Series(df.columns.str.replace("/ ", "")))

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

                    if np.array_equal(colset1, colset2) or (colset1.empty or colset2.empty):
                        single_moment = True
                    else:
                        single_moment = False

                    col_indices0 = np.asarray([np.int32(x.strip().split('_')[1]) for x in colset1], dtype=np.int32)
                    col_indices1 = np.asarray([np.int32(x.strip().split('_')[1]) for x in colset2], dtype=np.int32)

                    dimensions = {}
                    if gate_times is None:
                        pass
                    elif single_moment:
                        dimensions["gate_times"] = {"standard_name": "gate_times",
                                                          "long_name": "calibrated gate times",
                                                          "units": "seconds",
                                                          "missing_value": "not_defined",
                                                          "centers": gate_times}
                    else:
                        dimensions["lm_gate_times"] = {"standard_name": "lm_gate_times",
                                                          "long_name": "calibrated low moment gate times",
                                                          "units": "seconds",
                                                          "missing_value": "not_defined",
                                                          "centers": gate_times[col_indices0-1]}
                        dimensions["hm_gate_times"] = {"standard_name": "hm_gate_times",
                                                          "long_name": "calibrated high moment gate times",
                                                          "units": "seconds",
                                                          "missing_value": "not_defined",
                                                          "centers": gate_times[col_indices1-1]}
                    file_metadata = {'dimensions':dimensions} if dimensions else {}


                # iterate over mapping keys
                for segment, couplet in mapping.items():
                    if ft == 'dat':
                        prefix_dat = couplet + '_data_'
                        prefix_std = couplet + '_datastd_'
                    elif ft == 'syn':
                        prefix_dat = couplet + '_syn_'

                    # grab correct columns to merge
                    if single_moment:
                        couplet_data = df[df['SEGMENTS']==segment][colset1.insert(0, 'RECORD')]
                        if ft == 'dat':
                            colset1std = colset1.str.replace('DATA','DATASTD')
                            couplet_std = df[df['SEGMENTS']==segment][colset1std.insert(0, 'RECORD')]
                        colset=colset1
                    elif (segment == 1) | (segment == 3): #dual moment convention LM
                        couplet_data = df[df['SEGMENTS']==segment][colset1.insert(0, 'RECORD')]
                        if ft == 'dat':
                            colset1std = colset1.str.replace('DATA','DATASTD')
                            couplet_std = df[df['SEGMENTS']==segment][colset1std.insert(0, 'RECORD')]
                        colset=colset1
                    elif (segment == 2) | (segment == 4): #dual moment convention HM
                        couplet_data = df[df['SEGMENTS']==segment][colset2.insert(0, 'RECORD')]
                        if ft == 'dat':
                            colset2std = colset2.str.replace('DATA','DATASTD')
                            couplet_std = df[df['SEGMENTS']==segment][colset2std.insert(0, 'RECORD')]
                        colset=colset2

                    # merge into combined dataframe
                    for i, col in enumerate(colset):
                        datcol = f"{prefix_dat}{i+1}"
                        stdcol = f"{prefix_std}{i+1}"
                        df_combined = df_combined.merge(couplet_data[['RECORD',col]], how='left', on='RECORD')
                        df_combined = df_combined.rename(columns={col: datcol})
                        if ft == 'dat':
                            df_combined = df_combined.merge(couplet_std[['RECORD',col.replace('DATA','DATASTD')]], how='left', on='RECORD')
                            df_combined = df_combined.rename(columns={col.replace('DATA','DATASTD'): datcol.replace('data','datastd')})

        return df_combined, file_metadata