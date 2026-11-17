***************
Installing GSPy
***************

pip install gspy

File paths when running the examples
====================================

The example scripts read their data through relative paths built with
``os.path.join``. If you copy an example into a notebook and switch to an
absolute path, use a plain Windows path with single forward slashes, e.g.
``C:/Users/<name>/gspy/examples/data_files``.

A path containing a doubled forward slash is harmless on its own, but a path
whose prefix is written ``C://`` looks like a URL protocol to the file layer
(anything containing ``://`` is read as one). That is where errors like "fsspec
required", ".nc treated as a folder" or netCDF's ``OSError [Errno -36]`` come
from when opening or writing a file. Single slashes fix all three.