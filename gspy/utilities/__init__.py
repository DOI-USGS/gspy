def unique_list_preserve(this):
    out = []
    for item in this:
        if item not in out:
            out.append(item)
    return out

def same_length_lists(this):
    if this is None:
        return True
    if not isinstance(this[0], list):
        return True
    return all(len(l) == len(this[0]) for l in this)

def deprecated(func):
    def wrapper(*args, **kwargs):
        import warnings
        warnings.warn(
            f"Call to deprecated function {func.__name__}. Use new_function instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return wrapper