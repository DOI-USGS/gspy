import os
from pprint import pprint
import numpy as np
import xarray as xr
from ..utilities import unique_list_preserve, same_length_lists
from ..metadata.Metadata import Metadata
from ..metadata.Variable_metadata import Variable_metadata
# from ..gs_dataarray.DataArray import DataArray
from .Dataset import Dataset

required_keys = ('type',
                #  'structure',
                 'mode',
                 'method',
                 'submethod',
                 'instrument')

class System(Dataset):

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def is_projected(self):
        return False

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
    def open(cls, filename, **kwargs):
        md = Metadata.read(filename)
        for key,item in md.items():
            out = cls.from_dict(**item)
        return out

    @classmethod
    def from_dict(cls, **kwargs):
        attrs, kwargs = cls.pop_required(**kwargs)
        tmp = xr.Dataset(attrs=attrs)
        self = cls(tmp)

        for key, value in kwargs.pop('dimensions', {}).items():
            self._obj = self._obj.gs.add_coordinate_from_dict(key.lower(),
                                                 is_dimension=True,
                                                 **value)

        prefixes =  unique_list_preserve(['transmitter', 'receiver', 'component'] + kwargs.pop('prefixes', []))

        if 'variables' in kwargs:
            for prefix in prefixes:
                vars = kwargs['variables']
                if prefix == 'component' and 'component' in vars:
                    vars['component'] = self.__component_labels(**vars['component'])

                    if 'gate_times' in vars['component']:
                        vars['component']['gate_times'] = [x.lower() for x in vars['component']['gate_times']]

                self, kwargs['variables'] = self.__add_using_prefix(prefix, **kwargs['variables'])

            for key, values in kwargs['variables'].items():
                if not isinstance(values, dict):
                    values = dict(values=values)
                self._obj = self._obj.gs.add_variable_from_dict(name=key, check=False, **values)
            kwargs.pop('variables')

        # Cannot have literal Booleans in the attributes of a netcdf...
        # Convert to strings...
        for k, v in kwargs.items():
            if isinstance(v, bool):
                kwargs[k] = "True" if v else "False"

        self._obj.attrs = self._obj.attrs | kwargs

        return self._obj

    def __component_labels(self, **kwargs):
        kwargs['label'] = kwargs.get('receivers')
        if 'transmitters' in kwargs:
            kwargs['label'] = [f"{a}_{b}" for a, b in zip(kwargs['transmitters'], kwargs['label'])]
        return kwargs



    def __add_using_prefix(self, prefix, **kwargs):

        if prefix not in kwargs:
            return self, kwargs

        popped = kwargs.pop(prefix)

        label = popped.pop('label', None)
        if isinstance(label, dict):
            label = label['values']

        if len(popped) > 1:
            assert label is not None, ValueError(f"metadata for {prefix} given but no labels")

        if isinstance(label, str):
            label = [label]

        n_entries = np.size(label)

        self._obj = self.add_coordinate_from_values(f'n_{prefix}',
                                                values=np.arange(n_entries),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = f'number_of_{prefix}s',
                                                        long_name = f'Number of {prefix}s',
                                                        units = 'not_defined',
                                                        null_value = 'not_defined'))

        self, popped = self.add_dimensions_from_variables(prefix=prefix, label=label, **popped)
        popped.pop('prefix', None)
        for key, values in popped.items():
            if not isinstance(values, dict):
                if not isinstance(values, list):
                    values = np.full(n_entries, fill_value=values)
                values = dict(values=values)
            values['dimensions'] = values.pop('dimensions', f'n_{prefix}')
            self._obj = self._obj.gs.add_variable_from_dict(name=key, label=label, check=False, prefix=prefix, **values)

        return self, kwargs

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
