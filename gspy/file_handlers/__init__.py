"""Readers for the data formats GSPy ingests.

Each format is a subclass of :class:`gspy.file_handlers.file_handler` that
registers itself and says which files it recognises, so adding a format means
adding a module and importing it here.

>>> handler = open_datafile('Resolve.csv', metadata=md)   # reads the file
>>> handler.df, handler.columns, handler.nrecords, handler.file_metadata

Data already in memory goes in the same slot, so nothing downstream needs to
know where it came from:

>>> open_datafile(my_dataframe, metadata=md)   # adopted, no file touched
>>> open_datafile(handler, metadata=md)        # already read, metadata merged in

"""
from pandas import DataFrame

from .file_handler_abc import file_handler, InsufficientMetadataError
from .aseg_gdf_handler import aseg_gdf2_handler
from .csv_handler import csv_handler
from .dataframe_handler import dataframe_handler
from .loupe_handler import loupe_handler
from .xyz_handler import xyz_handler
from .workbench_handler import workbench_handler, workbench_model_handler


def handlers():
    """Every registered file handler, keyed by its format name.

    Returns
    -------
    dict

    """
    return dict(file_handler._registry)


def handler_for(filename, file_type=None):
    """The handler class that reads a file.

    Parameters
    ----------
    filename : str or pathlib.Path
        Data file.
    file_type : str, optional
        Name a format explicitly instead of detecting it, e.g. 'loupe'.

    Returns
    -------
    type
        A file_handler subclass.

    Raises
    ------
    ValueError
        If file_type is not a known format, or no format recognises the file.

    """
    registry = file_handler._registry

    if file_type is not None:
        key = str(file_type).lower()
        if key not in registry:
            raise ValueError(f"Unknown file_type {file_type!r}. "
                             f"Choose from {sorted(registry)}")
        return registry[key]

    claims = sorted((handler for handler in registry.values() if handler.can_read(filename)),
                    key=lambda handler: handler.priority, reverse=True)

    if not claims:
        raise ValueError(f"No file handler recognises {filename}. "
                         f"Pass file_type to choose one of {sorted(registry)}")

    return claims[0]


def open_datafile(data, metadata=None, file_type=None, **kwargs):
    """Get a handler for some data, reading it from disk only if it is a filename.

    Parameters
    ----------
    data : str or pathlib.Path or pandas.DataFrame or gspy.file_handlers.file_handler
        The data to ingest, as any of

        * a filename, read with whichever handler recognises it
        * a DataFrame already in memory, adopted as-is
        * a handler that has already read its file, returned unchanged

    metadata : dict, optional
        GSPy variable metadata. Merged over whatever the data declares about
        itself, so a definition file supplies the defaults and this overrides
        them.
    file_type : str, optional
        Name a format explicitly instead of detecting it, e.g. 'loupe'. Ignored
        unless ``data`` is a filename, since there is nothing to detect otherwise.

    Returns
    -------
    gspy.file_handlers.file_handler
        An instance whose ``df`` is populated.

    See Also
    --------
    handler_for : To choose the handler without reading.

    """
    if isinstance(data, file_handler):
        # Merge rather than replace: the handler may have gleaned column
        # descriptions from its own file, and those are the defaults here.
        data.combine_metadata(metadata)
        return data

    if isinstance(data, DataFrame):
        return dataframe_handler(data, metadata=metadata, **kwargs)

    return handler_for(data, file_type=file_type)(data, metadata=metadata, **kwargs)
