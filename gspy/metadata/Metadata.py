import os
from os.path import splitext
from ._json_md_handler import read_json, to_json
from ._yml_md_handler import read_yml, to_yml
from ._xl_md_handler import read_excel, to_excel
from ._csv_md_handler import read_csv, to_csv
import pprint

class Metadata(dict):

    def __init__(self, *args, required:tuple=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.required = required

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, values:tuple):
        if values is not None:
            self._required = values

    @classmethod
    def read(cls, filename):

        if filename is None:
            return {}

        if isinstance(filename, dict):
            out = cls(filename)._sort_out_list_of_strings()
            return out

        base, extension = splitext(filename)

        match extension:
            case '.json':
                out = read_json(filename)
            case '.yml':
                out = read_yml(filename)
            case '.yaml':
                out = read_yml(filename)
            case '.xlsx':
                out = read_excel(filename)
            case '.csv':
                out = read_csv(filename)
            case _:
                assert False, ValueError("metadata filename does not end with json or yml")

        out = cls(out)

        out = out._sort_out_list_of_strings()
        out['directory'] = os.path.split(filename)[0]
        return out

    @classmethod
    def merge(cls, this, that, matched_keys=False, **kwargs):
        """Unpacks a dictionary of dictionaries into a single dict with different keys

        Parameters
        ----------
        this : Dict
            Metadata to copy
        that : Dict
            Update this AND overwrite existing entries using that.

        Returns
        -------
        out : Metadata
            Merged dictionaries
        """
        # Create a copy of dict1 to avoid modifying it directly
        self = this.copy()

        # Update with dict2, overwriting existing entries
        for key, value in that.items():
            if key in self:
                if isinstance(value, dict):
                    self[key].update(value)
                else:
                    self[key] = value
            else:
                if not matched_keys:
                    self[key] = value

        return cls(self)

    def dump(self, filename, **kwargs):
        self.pop('directory', None)

        print(self.pop('directory', ""))


        base, extension = splitext(filename)

        match extension:
            case ".json":
                to_json(self, filename, **kwargs)
            case ".yml":
                to_yml(self, filename, **kwargs)
            case ".yaml":
                to_yml(self, filename, **kwargs)
            case ".xlsx":
                to_excel(self, filename, **kwargs)
            case ".csv":
                to_csv(self, filename, **kwargs)
            case _:
                raise Exception(f"Unknown extension for metadata file {filename}. Available types (json, yml, csv, xlsx)")


    def check_key_whitespace(self, flag=False):
        def __check_key_whitespace(this, flag=False):
            if not isinstance(this, dict):
                return flag
            for key, item in this.items():
                if ' ' in key:
                    print(f"{key=} contains whitespace. Please remove!")
                    key = key.strip()
                    flag = True
                flag = __check_key_whitespace(item, flag)
            return flag

        return __check_key_whitespace(self, flag=flag)

    def flatten(self):
        def __flatten(current, key='', result={}):
            """Unpacks a dictionary of dictionaries into a single dict with different keys
            """
            if isinstance(current, dict):
                for k in current:
                    new_key = f"{key.replace(' ','_')}.{k.replace(' ','_')}" if len(key) > 0 else k
                    __flatten(current[k], new_key, result)
            else:
                result[key] = current
            return result
        return __flatten(self)

    def unflatten(self):
        out = {}
        for key, item in self.items():
            if '.' in key:
                tmp = key.split('.')
                if not tmp[0] in out:
                    out[tmp[0]] = {}
                out[tmp[0]][tmp[1]] = item
            else:
                out[key] = item
        return out

    def __str__(self):
        return pprint.pformat(self)

    def print(self):
        pprint.pprint(self)

    def _sort_out_list_of_strings(self):
        for key, item in self.items():
            if isinstance(item, list):
                if all([isinstance(i, str) for i in item]):
                    self[key] = ','.join(a for a in item)
        return self

    def pop_and_split(self, keys:tuple):
        assert all([x in self for x in keys]), ValueError(f"System metadata must have entries for {keys}")
        popped = {}
        for k in keys:
            popped[k] = self.pop(k)
        return popped, self

    def check_keys(self, keys:tuple):
        assert all([x in self for x in keys]), ValueError(f"metadata must have entries for {keys}")