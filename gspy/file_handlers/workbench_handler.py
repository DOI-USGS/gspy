from warnings import warn

import numpy as np
from pandas import read_csv, Series, concat
from .xyz_handler import xyz_handler
from ..metadata.Metadata import Metadata

class _workbench_names:
    """Column naming, and the metadata template, shared by the Workbench exports.

    A subclass's read fills in ``_units`` and ``_gate_times``, and it gives
    ``_attrs``, ``_channel_columns`` and ``_template_dimensions``.
    """

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

    @classmethod
    def _bracket_units(cls, columns):
        """The unit a column carries in its name, m for ALTITUDE_[m], by tidied name."""
        units = columns.str.extract(r'_\[(\D[^\]]*)\]$')[0]
        return {name: unit for name, unit in zip(cls._tidied(columns), units) if isinstance(unit, str)}

    @staticmethod
    def _couplet_gate_times(system):
        """The gate times dimension each couplet label is measured on.

        Without gate times in the system, each transmitter's are named after it, the
        way System.metadata_template names them.
        """
        labels = system.gs.couplet_labels
        if 'couplet_gate_times' in system:
            return dict(zip(labels, (str(g) for g in system['couplet_gate_times'].values)))

        transmitters = [str(t).lower() for t in system['couplet_transmitters'].values]
        if len(set(transmitters)) == 1:
            return dict.fromkeys(labels, 'gate_times')
        return {label: f"{t}_gate_times" for label, t in zip(labels, transmitters)}

    def column_metadata(self, column):
        out = {'units': self._units[column]} if column in self._units else {}
        if column == 'ELEVATION':
            out['positive'] = 'up'
        for label, gates in self._gate_times.items():
            if column in self._channel_columns(label):
                out.update(dimensions=['index', gates], system_couplet=label)
        return out

    def metadata_template(self, **kwargs):
        out = super().metadata_template(**kwargs)

        out['dataset_attrs'] = Metadata.merge(Metadata.merge(out['dataset_attrs'], self._attrs),
                                              kwargs.get('dataset_attrs', {}))

        columns = self.df.columns
        coordinates = {axis: next((n for n in self.aliases(name) if n in columns), None)
                       for axis, name in (('x', 'UTMX'), ('y', 'UTMY'), ('z', 'ELEVATION'))}
        out['coordinates'] = Metadata.merge({k: v for k, v in coordinates.items() if v},
                                            kwargs.get('coordinates', {}))

        out['dimensions'] = Metadata.merge(self._template_dimensions(), kwargs.get('dimensions', {}))
        if 'layers_minus_1' in out['dimensions']:
            out.comments[('dimensions', 'layers_minus_1')] = {'above': [
                "The boundaries between layers, one fewer than there are layers. The",
                "per-boundary uncertainties, DEP_BOT_STD and THK_STD, use it."]}

        return out

    def combine_metadata(self, new, **kwargs):
        """A yml key keeping the underscore of a unit, ALTITUDE_ for ALTITUDE_[m],
        still describes the ALTITUDE column."""
        columns = self.column_header_counts
        renamed = {key: key.rstrip('_') for key in (new or {})
                   if key not in columns and key.rstrip('_') in columns}
        for old, name in renamed.items():
            warn(f"{old} in the metadata is read as {name}. Rename it, the trailing underscore is no longer needed.")

        if renamed:
            new = {renamed.get(key, key): value for key, value in new.items()}
        super().combine_metadata(new, **kwargs)

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

        self.metadata = {}
        header_gates, n_header = self.__parse_metadata(self.filename)

        system = system.gs.get_system_with_method('electromagnetic')

        mapping = {i+1:c_label for i, c_label in enumerate(system.gs.couplet_labels)}
        self._gate_times = self._couplet_gate_times(system)

        # The header's gate times, for the dimensions the system does not define.
        self._header_gates = {}
        for channel, label in mapping.items():
            name = self._gate_times[label]
            if name not in system.dims and channel in header_gates:
                self._header_gates.setdefault(name, header_gates[channel])

        self._df = self.read_data(self.filename, header=n_header, mapping=mapping)
        
        self.combine_metadata(metadata)

    _attrs = {'type': 'data', 'method': 'electromagnetic, time domain'}

    @staticmethod
    def _channel_columns(label):
        return (label.upper(), f"{label.upper()}_STD")

    def _template_dimensions(self):
        return {name: {'standard_name': name,
                       'long_name': 'gate times, from the data file header',
                       'units': 'seconds',
                       'missing_value': 'not_defined',
                       'centers': centers}
                for name, centers in self._header_gates.items()}

    def __parse_metadata(self, filename):
        """The gate times of each channel, and how many lines the header takes."""
        gates = dict()

        n_header = -1; done = False

        with open(filename, 'r') as file:
            while not done:
                n_header += 1
                line = file.readline()
                if 'Gates for channel' in line:
                    channel, times = line.split(':')
                    gates[int(channel.split()[-1])] = np.float64(times.split()).tolist()
                if 'DUMMY' in line:
                    line = file.readline()
                if 'DATE' in line:
                    n_header += 1
                    done = True

        return gates, n_header

    def read_data(self, filename, **kwargs):

        mapping = kwargs.pop('mapping')

        df = read_csv(filename, sep=r',\s+', engine='python', **kwargs)
        columns = Series(df.columns.str.replace(r'[,/ ]+', '',regex=True))
        self._units = self._bracket_units(columns)
        df.columns = self._tidied(columns)

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
        self._gate_times = self._couplet_gate_times(system)
        self._units = {}

        self._df, self._file_metadata = self.read_data(self.filename, mapping=mapping)

        if 'dimensions' not in self._file_metadata and 'couplet_gate_times' not in system:
            raise ValueError(f"{self.filename} does not list its gate times, as a multi-node export does not. "
                             "Define the gate times dimensions in the system yml, and name them with the couplet's gate_times.")

        self.combine_metadata(metadata)

    _attrs = {'type': 'models', 'method': 'electromagnetic, time domain',
              'property': 'electrical resistivity'}

    @staticmethod
    def _channel_columns(label):
        return (f"{label}_data", f"{label}_datastd", f"{label}_syn")

    def column_metadata(self, column):
        out = super().column_metadata(column)
        n_layers, count = self.column_header_counts.get('RHO'), self.column_header_counts[column]
        if n_layers and count > 1 and 'dimensions' not in out:
            dimension = {n_layers: 'layer_depth', n_layers - 1: 'layers_minus_1'}.get(count)
            if dimension:
                out['dimensions'] = ['index', dimension]
        return out

    def _template_dimensions(self):
        """The layers, bounded by DEP_TOP and DEP_BOT where every record shares them."""
        n_layers = self.column_header_counts.get('RHO')
        if not n_layers:
            return {}

        layers = {'standard_name': 'layer_depth',
                  'long_name': 'Depth to the top and bottom of each model layer',
                  'units': self._units.get('DEP_TOP', 'm'),
                  'missing_value': 'not_defined'}
        depths = [self.df.filter(regex=rf'^{name}_\d+$') for name in ('DEP_TOP', 'DEP_BOT')]
        if all(d.shape[1] == n_layers and (d.nunique() == 1).all() for d in depths):
            layers['bounds'] = [d.iloc[0].tolist() for d in depths]
        else:
            layers.update(origin=0, increment=1, length=n_layers)

        return {'layer_depth': layers,
                'layers_minus_1': {'standard_name': 'layers_minus_1',
                                   'long_name': 'Index of the boundary between two model layers',
                                   'units': 'not_defined',
                                   'missing_value': 'not_defined',
                                   'origin': 0, 'increment': 1, 'length': n_layers - 1}}

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
            columns = Series(df.columns.str.replace("/ ", ""))
            self._units |= self._bracket_units(columns)
            df.columns = self._tidied(columns)

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