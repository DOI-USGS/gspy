import os
from pprint import pprint
import numpy as np
import xarray as xr
# from ...utilities import dump_metadata_to_file
from ..metadata.Metadata import Metadata
from .xarray_gs.Dataset import Dataset

required_keys = ('type',
                 'mode',
                 'method',
                 'submethod',
                 'instrument')

@xr.register_dataset_accessor("gs_system")
class System(Dataset):

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def is_projected(self):
        return False

    @classmethod
    def from_dict(cls, **kwargs):

        if kwargs.get('method', None) == "electromagnetic":
            self = cls.add_electromagnetic_system(**kwargs)

        else:
            self = cls.add_generic_system(**kwargs)

        return self._obj

    def check_against_data(self, dataset):
        """Assert that gate time strings match the coordinates of the attached dataset.
        """
        for gt in self._obj['component_gate_times']:
            assert gt in list(dataset.coords.keys()), ValueError(f"Could not match component gate times {gt} to dataset coordinates")

    @staticmethod
    def check_required(**kwargs):
        assert all([x in kwargs for x in required_keys]), ValueError(f"System metadata must have entries for {required_keys}")

    @staticmethod
    def pop_required(**kwargs):

        assert all([x in kwargs for x in required_keys]), ValueError(f"System metadata must have entries for {required_keys}")
        required = {}
        for k in required_keys:
            required[k] = kwargs.pop(k)
        return required, kwargs

    @classmethod
    def add_generic_system(cls, **kwargs):
        attrs, kwargs = cls.pop_required(**kwargs)
        tmp = cls(xr.Dataset(attrs=attrs))

        if "dimensions" in kwargs:
            for key, value in kwargs['dimensions'].items():
                tmp = tmp.add_coordinate_from_dict(key.lower(), discrete=True, is_dimension=True, check=False, **value)

        if "variables" in kwargs:
            for key, value in kwargs['variables'].items():
                assert value is not None, ValueError(f"metadata does not exist for {key}")
                tmp = tmp.add_variable_from_values(key.lower(), check=False, **value)

        return tmp

    @classmethod
    def add_magnetic_system(cls, **kwargs):
        return cls.add_generic_system(**kwargs)


    @classmethod
    def add_electromagnetic_system(cls, **kwargs):
        cls.check_required(**kwargs)
        if kwargs['submethod'] == "time domain":
            return cls.add_time_domain_system(**kwargs)
        else:
            return cls.add_frequency_domain_system(**kwargs)

    @classmethod
    def add_frequency_domain_system(cls, **kwargs):
        attrs, kwargs = cls.pop_required(**kwargs)
        tmp = xr.Dataset(attrs=attrs)
        self = cls(tmp)

        assert "dimensions" in kwargs, ValueError("system metadata must have dimensions defined for gate times")

        for key, value in kwargs['dimensions'].items():
            self = self.add_coordinate_from_dict(key.lower(),
                                                 is_dimension=True,
                                                 **value)

        return self

    @classmethod
    def add_time_domain_system(cls, **kwargs):
        attrs, kwargs = cls.pop_required(**kwargs)
        tmp = xr.Dataset(attrs=attrs)
        self = cls(tmp)

        assert "dimensions" in kwargs, ValueError("system metadata must have dimensions defined for gate times")

        for key, value in kwargs['dimensions'].items():
            self = self.add_coordinate_from_dict(key.lower(),
                                                 is_dimension=True,
                                                 **value)

        self = self.add_transmitters(**{k: v for k, v in kwargs.items() if k.startswith('transmitter_')})
        self = self.add_receivers(**{k: v for k, v in kwargs.items() if k.startswith('receiver_')})
        self = self.add_components(**{k: v for k, v in kwargs.items() if k.startswith('component_')})

        return self

    def add_components(self, **kwargs):
        self = self.add_coordinate_from_values('n_components',
                                                values=np.arange(np.size(kwargs.get('component_transmitters'))),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = 'component_transmitters',
                                                        long_name = 'transmitter for each component',
                                                        units = 'not_defined',
                                                        null_value = 'not_defined'))

        self = self.add_variable_from_values('component_transmitters',
                                             values=kwargs.pop('component_transmitters'),
                                             dimensions = ('n_components', ),
                                             **dict(standard_name = 'component_transmitters',
                                                    long_name = 'Transmitter for each component',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('component_receivers',
                                             values=kwargs.pop('component_receivers'),
                                             dimensions = ('n_components', ),
                                             **dict(standard_name = 'component_receivers',
                                                    long_name = 'Receiver for each component',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        if "component_sample_rate" in kwargs:
            self = self.add_variable_from_values('component_sample_rate',
                                                    values=np.asarray(kwargs.pop('component_sample_rate'), dtype=np.float64),
                                                    dimensions = ('n_components', ),
                                                    **dict(standard_name = 'component_sample_rate',
                                                        long_name = 'Sampling rate of this component',
                                                        units = kwargs.get('component_sampe_rate_units', 's'),
                                                        null_value = 'not_defined'))

        self = self.add_variable_from_values('component_txrx_dx',
                                             values=np.asarray(kwargs.pop('component_txrx_dx'), dtype=np.float64),
                                             dimensions = ('n_components', ),
                                             **dict(standard_name = 'component_txrx_dx',
                                                    long_name = 'x offset for each transmitter receiver pair',
                                                    units = 'm',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('component_txrx_dy',
                                             values=np.asarray(kwargs.pop('component_txrx_dy'), dtype=np.float64),
                                             dimensions = ('n_components', ),
                                             **dict(standard_name = 'component_txrx_dy',
                                                    long_name = 'y offset for each transmitter receiver pair',
                                                    units = 'm',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('component_txrx_dz',
                                             values=np.asarray(kwargs.pop('component_txrx_dz'), dtype=np.float64),
                                             dimensions = ('n_components', ),
                                             **dict(standard_name = 'component_txrx_dz',
                                                    long_name = 'vertical offset for each transmitter receiver pair',
                                                    units = 'm',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('component_gate_times',
                                             values=kwargs.pop('component_gate_times'),
                                             dimensions = ('n_components', ),
                                             **dict(standard_name = 'component_gate_times',
                                                    long_name = 'Gate times for this component',
                                                    units = 's',
                                                    null_value = 'not_defined'))

        return self

    def add_transmitters(self, **kwargs):
        n_transmitters = np.size(kwargs.get('transmitter_label'))

        if n_transmitters == 1:
            kwargs = {k:np.atleast_1d(v) for k,v in kwargs.items()}


        self = self.add_coordinate_from_values('n_transmitters',
                                                values=np.arange(n_transmitters),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = 'number_of_transmitters',
                                                        long_name = 'Number of transmitter loops in this system',
                                                        units = 'not_defined',
                                                        null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_label',
                                             values=kwargs.pop('transmitter_label'),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter label',
                                                    long_name = 'Label of the transmitter',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_area',
                                             values=np.asarray(kwargs.pop('transmitter_area'), dtype=np.float64),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter area',
                                                    long_name = 'Loop area of the transmitter',
                                                    units = r'm^{2}',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_base_frequency',
                                             values=np.asarray(kwargs.pop('transmitter_base_frequency'), dtype=np.float64),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter base frequency',
                                                    long_name = 'Base frequency of the transmitter',
                                                    units = 'Hz',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_current_scale_factor',
                                             values=np.asarray(kwargs.pop('transmitter_current_scale_factor', np.ones(n_transmitters)), dtype=np.float64),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter current scale factor',
                                                    long_name = 'Current scale factor of the transmitter',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_number_of_turns',
                                             values=np.asarray(kwargs.pop('transmitter_number_of_turns'), dtype=np.int32),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'number_of_transmitter_turns',
                                                    long_name = 'Number of loops turns of the transmitter',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_on_time',
                                             values=np.asarray(kwargs.pop('transmitter_on_time'), dtype=np.float64),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter_on_time',
                                                    long_name = 'On time of the transmitter',
                                                    units = 's',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_off_time',
                                             values=np.asarray(kwargs.pop('transmitter_off_time'), dtype=np.float64),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter_off_time',
                                                    long_name = 'Off time of the transmitter',
                                                    units = 's',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_orientation',
                                             values=kwargs.pop('transmitter_orientation'),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter_orientation',
                                                    long_name = 'Orientation of the transmitter loop',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_peak_current',
                                             values=np.asarray(kwargs.pop('transmitter_peak_current'), dtype=np.float64),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter_peak_current',
                                                    long_name = 'Peak current of the transmitter',
                                                    units = 'A',
                                                    null_value = 'not_defined'))

        self = self.add_variable_from_values('transmitter_waveform_type',
                                             values=kwargs.pop('transmitter_waveform_type'),
                                             dimensions = ('n_transmitters', ),
                                             **dict(standard_name = 'transmitter_waveform_type',
                                                    long_name = 'Waveform type of the transmitter',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        time = kwargs.pop('transmitter_waveform_time')
        current = kwargs.pop('transmitter_waveform_current')

        if n_transmitters == 1:
            time = [time]
            current = [current]

        for i, (t, c) in enumerate(zip(time, current)):
            l = self._obj['transmitter_label'][i].item().lower()

            self = self.add_coordinate_from_values(
                f'{l}_waveform_time',
                values=np.asarray(t, dtype=np.float64),
                is_dimension=True,
                discrete=True,
                **dict(standard_name = f'{l}_waveform_time',
                        long_name = f'{l} waveform time',
                        units = 's',
                        null_value = 'not_defined'))

            self = self.add_variable_from_values(f'{l}_waveform_current',
                                             values=np.asarray(c, dtype=np.float64),
                                             dimensions = (f'{l}_waveform_time', ),
                                             **dict(standard_name = f'{l}_waveform_current',
                                                    long_name = f'{l} waveform current',
                                                    units = 'A',
                                                    null_value = 'not_defined'))

        self = self.add_coordinate_from_values(f'xyz',
                                                values=np.arange(3),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = 'xyz dimensions',
                                                        long_name = "spatial dimensions of the loop vertices",
                                                        units = 'm',
                                                        null_value = 'not_defined'))

        if 'transmitter_coordinates' in kwargs:

            tcoords = kwargs['transmitter_coordinates']
            if np.ndim(tcoords) == 2:
                tcoords = [tcoords]

            for i in range(self._obj.sizes['n_transmitters']):
                c = tcoords[i]
                l = self._obj['transmitter_label'][i].item().lower()

                self = self.add_coordinate_from_values(f'{l}_loop_vertices',
                                                    values=np.asarray(np.arange(np.size(c, 0)), dtype=np.float64),
                                                    is_dimension=True,
                                                    discrete=True,
                                                    **dict(standard_name = f'{l}_loop_vertices',
                                                            long_name = "loop vertices",
                                                            units = 'not_defined',
                                                            null_value = 'not_defined'))

                self = self.add_variable_from_values(f'{l}_loop_coordinates',
                                                    values=np.asarray(c, dtype=np.float64),
                                                    dimensions = (f'{l}_loop_vertices', 'xyz'),
                                                    **dict(standard_name = f'{l}_loop_coordinates',
                                                            long_name = f'{l} loop coordinates',
                                                            units = 'm',
                                                            null_value = 'not_defined'))

        return self



    def add_receivers(self, **kwargs):
        self = self.add_coordinate_from_values('n_receivers',
                                                values = np.arange(np.size(kwargs.get('receiver_label'))),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = 'number_of_receivers',
                                                        long_name = 'Number of receiver loops in this system',
                                                        units = 'not_defined',
                                                        null_value = 'not_defined'))

        self = self.add_variable_from_values('receiver_label',
                                             values = kwargs.pop('receiver_label'),
                                             dimensions = ('n_receivers', ),
                                             **dict(standard_name = 'receiver label',
                                                    long_name = 'Label of the receiver',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        if "receiver_coil_low_pass_filter" in kwargs:
            self = self.add_variable_from_values('receiver_coil_low_pass_filter',
                                                values = np.asarray(kwargs.pop('receiver_coil_low_pass_filter'), dtype=np.float64),
                                                dimensions = ('n_receivers', ),
                                                **dict(standard_name = 'receiver_coil_low_pass_filter',
                                                        long_name = 'Low pass filter frequencey of the coil',
                                                        units = 'Hz',
                                                        null_value = 'not_defined'))

        self = self.add_variable_from_values('receiver_orientation',
                                             values = kwargs.pop('receiver_orientation'),
                                             dimensions = ('n_receivers', ),
                                             **dict(standard_name = 'receiver_orientation',
                                                    long_name = 'Orientation of the receiver loop',
                                                    units = 'not_defined',
                                                    null_value = 'not_defined'))

        if "receiver_instrument_low_pass_filter" in kwargs:
            self = self.add_variable_from_values('receiver_instrument_low_pass_filter',
                                                values = np.asarray(kwargs.pop('receiver_instrument_low_pass_filter'), dtype=np.float64),
                                                dimensions = ('n_receivers', ),
                                                **dict(standard_name = 'receiver_instrument_low_pass_filter',
                                                        long_name = 'Low pass filter frequency of the instrument',
                                                        units = 'Hz',
                                                        null_value = 'not_defined'))

        if "receiver_area" in kwargs:
            self = self.add_variable_from_values('receiver_area',
                                                    values = np.asarray(kwargs.pop('receiver_area'), dtype=np.float64),
                                                    dimensions = ('n_receivers', ),
                                                    **dict(standard_name = 'receiver_area',
                                                        long_name = 'Area of the receiver loop',
                                                        units = r'm^{2}',
                                                        null_value = 'not_defined'))

        return self

    @classmethod
    def valid_model(cls, **kwargs):
        return kwargs["mode"] in ("airborne", "waterborne", "ground", "borehole")

    @classmethod
    def valid_method(cls, **kwargs):
        return kwargs["method"] in ("electromagnetic", "magnetic", "gravity", "galvanic", "nmr")

    @classmethod
    def valid_submethod(cls, **kwargs):
        return kwargs["submethod"] in ("frequency domain", "time domain", "direct current", "induced polarization", "total field", "gradiometry", "absolute")

    @classmethod
    def valid_instrument(cls, **kwargs):
        return any(x in kwargs["instrument"] for x in ('resolve', 'skytem', 'tempest', 'cesium vapour'))

