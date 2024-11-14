import json
import yaml

def check_key_whitespace(this, flag=False):
    if not isinstance(this, dict):
        return flag
    for key, item in this.items():
        if ' ' in key:
            print('key "{}" contains whitespace. Please remove!'.format(key))
            key = key.strip()
            flag = True
        flag = check_key_whitespace(item, flag)
    return flag

def flatten(current, key, result):
    """Unpacks a dictionary of dictionaries into a single dict with different keys
    """
    if isinstance(current, dict):
        for k in current:
            new_key = "{0}.{1}".format(key.replace(' ','_'), k.replace(' ','_')) if len(key) > 0 else k
            flatten(current[k], new_key, result)
    else:
        result[key] = current
    return result

def unflatten(old):
    out = {}
    for key, item in old.items():
        if '.' in key:
            tmp = key.split('.')
            if not tmp[0] in out:
                out[tmp[0]] = {}
            out[tmp[0]][tmp[1]] = item
        else:
            out[key] = item
    return out

def dump_metadata_to_file(dic, filename):

    with open(filename, "w") as f:
        if 'json' in filename:
            json.dump(dic, f, indent=4)
        elif 'yml' in filename:
            yaml.dump(dic, f)
        else:
            raise Exception("Unknown extension for metadata file {}, please use json or yml".format(filename))

def load_metadata_from_file(filename, **kwargs):
    with open(filename) as f:
        if 'json' in filename:
            md = json.loads(f.read())
        elif 'yml' in filename:
            md = yaml.safe_load(f)
    return md