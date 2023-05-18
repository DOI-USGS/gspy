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