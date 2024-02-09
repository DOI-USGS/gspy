**********************************************
Importing aseg-gdf2 files into the GSPy Survey
**********************************************

You can directly import aseg-gdf2 files with a .dat and .dfn file.
Pratt, D. A. (2003). ASEG-GDF2 A Standard for Point Located Data Exchange.
Australian Society of Exploration Geophysicists, 4(0), 1-34.
https://www.aseg.org.au/sites/default/files/pdf/ASEG-GDF2-REV4.pdf

We do not handle importing .des or .met files that seem to be deprecated.

Mapping the DFN to the CF metadata convention
=============================================
The following is an example of a dfn metadata entry

DEFN  9 ST=RECD,RT=;Latitude:f12.7:UNIT=deg:NULL=-99.9999999,NAME=Latitude

which we map to the CF metadata attributes standard_name, long_name, units, and null_value as follows.

Latitude becomes the standard_name, and is converted to all lower case.
UNIT becomes units, NULL becomes null_value.
NAME becomes the longer description call long_name

The dfn file also contains a fortran format entry, e.g, f12.7, i5, a16, etc.
We maintain that fortran format in the GSPy metadata in case a user wants to export a GSPy dataset to ASEG-GDF2 files.

If entries are not provided for NAME, UNIT, NULL, we simply enter "not_defined" in the GSPy file. It is upto the user then to complete the metadata entry.

When importing aseg_gdf2 files into GSPy, you can provide additional metadata via either json or yml files. See our examples section for more info.
**The entries in the yml file will overwrite the dfn file entries.**
