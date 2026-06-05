import os
import numpy as np
import xarray as xr
from ..metadata.Metadata import Metadata
# from ..gs_dataarray.DataArray import DataArray
from .Dataset import Dataset

required_keys = ('type',
                #  'structure',
                 'mode',
                 'method',
                 'instrument')

class Parameters(Dataset):

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def is_projected(self):
        return False

    @staticmethod
    def pop_required(**kwargs):
        required = {}
        for k in required_keys:
            required[k] = kwargs.pop(k)
        return required, kwargs

    @classmethod
    def open(cls, filename, **kwargs):
        md = Metadata.read(filename)
        #print(md)
        #for key,item in md.items():
            # print('in open')
            # print(key, item)
            #if key == 'dataset_attrs':
            #    assert all([x in item.keys() for x in required_keys]), ValueError(f"Parameters metadata must have entries for {required_keys}")
            
        out = cls.from_dict(**md)
        return out

    @classmethod
    def from_dict(cls, **kwargs):
        
        #attrs, kwargs = cls.pop_required(**kwargs)
        dattrs = kwargs.pop('dataset_attrs', {})
        assert all([x in dattrs.keys() for x in required_keys]), ValueError(f"Parameters metadata must have entries for {required_keys} in dataset_attrs")
        tmp = xr.Dataset(attrs=dattrs)
        self = cls(tmp)

        for key, value in kwargs.pop('dimensions', {}).items():
            self._obj = self._obj.gs.add_coordinate_from_dict(key.lower(),
                                                 is_dimension=True,
                                                 **value)

        prefixes =  kwargs.pop('prefixes', [])

        if 'variables' in kwargs:
            for prefix in prefixes:
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

        self._obj = self.add_coordinate_from_values(f"n_{prefix}",
                                                values=np.arange(n_entries),
                                                is_dimension=True,
                                                discrete=True,
                                                **dict(standard_name = f"number_of_{prefix}s",
                                                        long_name = f"Number of {prefix}s",
                                                        units = "not_defined",
                                                        null_value = "not_defined"))

        self, popped = self.add_dimensions_from_variables(prefix=prefix, label=label, **popped)
        popped.pop('prefix', None)
        for key, values in popped.items():
            if not isinstance(values, dict):
                if not isinstance(values, list):
                    values = np.full(n_entries, fill_value=values)
                values = dict(values=values)
            values['dimensions'] = values.pop('dimensions', f"n_{prefix}")
            self._obj = self._obj.gs.add_variable_from_dict(name=key, label=label, check=False, prefix=prefix, **values)

        return self, kwargs