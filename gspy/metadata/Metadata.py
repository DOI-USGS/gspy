from os.path import splitext
import json
import yaml
from pprint import pprint

class Metadata(dict):

    @classmethod
    def read(cls, filename):

        if filename is None:
            return {}

        if isinstance(filename, dict):
            out = cls(filename)._sort_out_list_of_strings()
            return out

        with open(filename) as f:
            filename = filename.replace('yaml', 'yml')

            base, extension = splitext(filename)

            match extension:
                case '.json':
                    out = cls(json.loads(f.read()))
                case '.yml':
                    out =  cls(yaml.safe_load(f))
                case _:
                    assert False, ValueError("metadata filename does not end with json or yml")

        out = out._sort_out_list_of_strings()
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

    def dump(self, filename):
        def __yaml_dump(this, file, indent=0, key=None):
            if isinstance(this, dict):
                if key is not None:
                    file.write(f"{'    '*indent}{key}:\n")
                    indent += 1
                for key, value in this.items():
                    __yaml_dump(value, file, indent=indent, key=key)
            else:
                file.write(f"{'    '*indent}{key}: {this}\n")

        with open(filename, "w") as f:
            if 'json' in filename:
                json.dump(self, f, indent=4)
            elif 'yml' in filename:
                __yaml_dump(self, f)
            else:
                raise Exception(f"Unknown extension for metadata file {filename}, please use json or yml")

    def check_key_whitespace(self, flag=False):
        def __check_key_whitespace(this, flag=False):
            if not isinstance(this, dict):
                return flag
            for key, item in this.items():
                if ' ' in key:
                    print(f'{key=} contains whitespace. Please remove!')
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

    def print(self):
        pprint(self)

    def _sort_out_list_of_strings(self):
        for key, item in self.items():
            if isinstance(item, list):
                if all([isinstance(i, str) for i in item]):
                    self[key] = ','.join(a for a in item)
        return self