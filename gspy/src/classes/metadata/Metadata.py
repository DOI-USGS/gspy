import json
import yaml
from pprint import pprint

class Metadata(dict):

    @classmethod
    def read(cls, filename):

        if isinstance(filename, dict):
            return filename

        with open(filename) as f:
            filename = filename.replace('yaml', 'yml')
            if 'json' in filename:
                return cls(json.loads(f.read()))
            elif 'yml' in filename:
                return cls(yaml.safe_load(f))

        assert False, ValueError("metadata filename does not end with json or yml")

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

        print(Warning(f"Writing metadata to {filename}.  Entries that need filling in are denoted with '??'"))

        def __yaml_dump(this, file, indent=0, key=None):
            if isinstance(this, dict):
                if key is not None:
                    file.write(f"{"    "*indent}{key}:\n")
                    indent += 1
                for key, value in this.items():
                    __yaml_dump(value, file, indent=indent, key=key)
            else:
                file.write(f"{"    "*indent}{key}: {this}\n")

        with open(filename, "w") as f:
            if 'json' in filename:
                json.dump(self, f, indent=4)
            elif 'yml' in filename:
                __yaml_dump(self, f)
            else:
                raise Exception("Unknown extension for metadata file {}, please use json or yml".format(filename))

    def check_key_whitespace(self, flag=False):
        def __check_key_whitespace(this, flag=False):
            if not isinstance(this, dict):
                return flag
            for key, item in this.items():
                if ' ' in key:
                    print('key "{}" contains whitespace. Please remove!'.format(key))
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
                    new_key = "{0}.{1}".format(key.replace(' ','_'), k.replace(' ','_')) if len(key) > 0 else k
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