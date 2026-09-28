"""How GSPy lays a variable out when it writes one: compressed, shuffled, chunked."""
import os

import h5py
import numpy as np

# Shuffle groups the bytes of each value by position, which is where gzip finds the
# repetition in neighbouring floats. netCDF4 turns it on by itself, h5netcdf does not.
DEFAULT_COMPRESSION = dict(zlib=True, complevel=4, shuffle=True)

# h5py's default chunk cache per dataset. A chunk that fits is decompressed once
# however many partial reads touch it; one that does not is decompressed every time.
CHUNK_BYTES = 2**20

COMPRESSION_KEYS = set(DEFAULT_COMPRESSION) | {"compression", "compression_opts"}
CHUNK_KEYS = {"chunksizes", "chunks"}

# How a variable's values are written, as opposed to how they are laid out. A
# variable read from a file carries these, and passing an encoding replaces the
# variable's own outright, so they are carried over.
VALUE_KEYS = {"dtype", "_FillValue", "missing_value", "scale_factor", "add_offset",
              "units", "calendar", "_Unsigned"}


# netCDF's own fill for each integer type, used where no missing value is stated.
DEFAULT_FILLS = {np.dtype(kind): fill for kind, fill in [
    ("i1", -127), ("u1", 255), ("i2", -32767), ("u2", 65535),
    ("i4", -2147483647), ("u4", 4294967295),
    ("i8", -9223372036854775806), ("u8", 18446744073709551614)]}


def chunk_shape(shape, itemsize, target=CHUNK_BYTES):
    """The shape to chunk an array by, or None if it cannot be chunked.

    Halves the longest dimension until a chunk fits ``target``. Soundings are cut
    long before gates, so a transient stays in one chunk, and a grid comes out in
    near square tiles.

    """
    if not shape or 0 in shape:
        return None

    chunks = list(shape)
    while np.prod(chunks) * itemsize > target and max(chunks) > 1:
        longest = int(np.argmax(chunks))
        chunks[longest] = -(-chunks[longest] // 2)

    return tuple(int(chunk) for chunk in chunks)


def missing_value(variable):
    """The number a variable states is missing, or None for a placeholder.

    GSPy states ``'not_defined'`` rather than leave ``missing_value`` out.

    """
    missing = variable.encoding.get("missing_value", variable.attrs.get("missing_value"))
    if missing is None or np.asarray(missing).dtype.kind not in "iuf":
        return None
    return missing


def fill_value(name, variable, dtype):
    """The ``_FillValue`` to write ``variable`` with as ``dtype``.

    A stated missing value, else a fill the variable already carries, else NaN for a
    float and netCDF's default for an integer. None for a dimension coordinate, which
    CF allows no missing values.

    """
    missing = missing_value(variable)
    if missing is not None:
        return missing
    if "_FillValue" in variable.encoding:
        return variable.encoding["_FillValue"]
    if name in variable.dims:
        return None
    if dtype.kind == "f":
        return np.nan
    return DEFAULT_FILLS[dtype]


def default_filled_integers(path):
    """Names of the integer variables in a file filled only with netCDF's default.

    Masking one would turn it to float for a fill that marks nothing, so these are
    read unmasked. A name counts only if it qualifies in every group it is in.

    """
    if not isinstance(path, (str, os.PathLike)):
        return set()

    verdicts = {}
    def judge(key, item):
        if not isinstance(item, h5py.Dataset) or "_FillValue" not in item.attrs:
            return
        attrs = item.attrs
        missing = attrs.get("missing_value")
        default = (item.dtype in DEFAULT_FILLS
                   and attrs["_FillValue"] == DEFAULT_FILLS[item.dtype]
                   and (missing is None or np.asarray(missing).dtype.kind not in "iuf")
                   and "scale_factor" not in attrs and "add_offset" not in attrs)
        name = key.rsplit("/", 1)[-1]
        verdicts[name] = verdicts.get(name, True) and default

    try:
        with h5py.File(path, "r") as handle:
            handle.visititems(judge)
    except OSError:
        return set()
    return {name for name, default in verdicts.items() if default}


def unmasked(path, kwargs):
    """``kwargs`` for an xarray opener, reading default-filled integers as integers."""
    if "mask_and_scale" not in kwargs and kwargs.get("decode_cf", True):
        names = default_filled_integers(path)
        if names:
            kwargs["mask_and_scale"] = {name: False for name in names}
    return kwargs


def restore_fill_values(variables):
    """Move a ``_FillValue`` left on the attributes by an unmasked read onto the
    encoding, where decoding would have put it and where writing expects it."""
    for variable in variables:
        if "_FillValue" in variable.attrs:
            variable.encoding["_FillValue"] = variable.attrs.pop("_FillValue")


def restore_placeholders(variables):
    """Put a placeholder ``missing_value`` read from a file back on the attributes.

    Decoding moves it onto the encoding, where xarray casts it to the variable's
    dtype on write: no number for a float, a numpy string h5py cannot store for text.

    """
    for variable in variables:
        if isinstance(variable.encoding.get("missing_value"), (str, bytes)):
            variable.attrs["missing_value"] = variable.encoding.pop("missing_value")


def dataset_encoding(dataset, compression=True, given=None):
    """``{variable: encoding}`` to write ``dataset`` with.

    Every numeric variable with a dimension is compressed and chunked; strings are
    left to xarray. Every numeric variable but a boolean gets a ``_FillValue``, as CF
    asks, compressed or not: see ``fill_value``. A numeric missing value is the fill
    value, since otherwise the file would state two.

    Parameters
    ----------
    dataset : xarray.Dataset
    compression : bool or dict, optional
        True for DEFAULT_COMPRESSION, False for none, or a dict laid over the
        defaults, e.g. ``dict(complevel=9)``.
    given : dict, optional
        ``{variable: encoding}`` from the caller. Naming any compression setting
        replaces the compression for that variable, naming chunks replaces the
        chunks, and anything else is added.

    Returns
    -------
    dict

    """
    given = dict(given or {})

    settings = None
    if compression is not False:
        settings = dict(DEFAULT_COMPRESSION)
        if isinstance(compression, dict):
            settings.update(compression)

    encoding = {}
    for name, variable in dataset.variables.items():
        if variable.dtype.kind not in "biuf":
            continue

        values = {key: value for key, value in variable.encoding.items() if key in VALUE_KEYS}
        dtype = np.dtype(values.get("dtype", variable.dtype))
        if dtype.kind in "iuf":
            values["_FillValue"] = fill_value(name, variable, dtype)

        chunks = None
        if settings is not None and variable.ndim > 0:
            chunks = chunk_shape(variable.shape, dtype.itemsize)

        stated = given.pop(name, {})
        layout = {}
        if chunks is not None:
            if not COMPRESSION_KEYS & set(stated):
                layout.update(settings)
            if not CHUNK_KEYS & set(stated):
                layout["chunksizes"] = chunks

        encoding[name] = {**values, **layout, **stated}

    return {**encoding, **given}
