#######################
Data Leaf Metadata File
#######################

GSPy uses metadata files (YAML or JSON) to ingest required and ancillary information and build the Data Tree. 

The Data Leaf Metadata File must contain the required sections ``dataset_attrs`` and ``coordinates``. 

The sections ``dimensions`` and ``variables`` are often commonly required, depending on the data type. 

Lastly, sections with the suffix ``_system`` are automatically identified by GSPy and added to the Data Leaf group as a Supplementary Leaflet. Systems can also be included in the Survey metadata file, for easy access to copy systems through when adding data leaves later on. However, when writing to netCDF, all systems attached to the '/survey' group directly are dropped. 

Any additional sections  are optional at the user's discretion. 

Dataset Attributes
------------------

Global attributes for the Data Leaf group are passed through the dataset attributes, ``dataset_attrs``. The GS standard requires and recommends multiple specific keys, explained on :doc:`this page <index>`.

The GSPy package automatically adds the ``structure`` key when reading in data files based on the type of file (tabular vs. raster). 

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 1-10

Coordinates
-----------

The four standardized coordinate variables (x, y, z, and t) are specificed through the ``coordinates`` dictionary, which is simply a key mapping to the variables the user wants to designate as the coordinates. 

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 11-17


GSPy automatically adds the required CF attribute ``axis`` with the values 'X', 'Y', 'Z', or 'T' to these coordinate variables for universal identification. 

The vertical ``z`` and time ``t`` coordinates both require the attribute ``datum``, and the ``z`` coordinate additionally requires ``positive`` indicating 'up' or 'down', per CF conventions. These attributes are passed through the variables dictionary (see further below).

Dimensions
----------

Underneath the "dimensions" header, any subsection will become a dimension coordinate with the title corresponding to its variable name (e.g. "layer_depth"). GSPy will generate the values of the dimension coordinate through multiple options:

- if "centers" are passed, without "bounds":
   - the 1-D list becomes the coordinate values
   - if "discrete: True" is passed, then no bounds are calculated, otherwise GSPy with automatically generate a "bounds" variable based on the spacing of the centers.
- if "bounds" are passed, without centers:
   - the "bounds" should be a 2 x N list, where N is the length of the dimension
   - the "centers" are automatically generated based on the widths of the bounds
- if "centers" and "bounds" are both passed:
   - both "bounds" and "centers" are defined directly based on the values passed. "centers" should be a 1-D list of length N, and "bounds" should be a 2-D list and can be either (2, N) or (N, 2).
- Using the fields "length", "increment", and "origin":
   - GSPy with automatically generate a 1-D array corresponding to the centers of the dimension starting at the origin and incrementing evenly to the total length defined.
   - If only "length" is passed the "origin" is assumed to be zero and the "increment" is one. 
   - As before, if "discrete: True" is passed, then no bounds are calculated, otherwise a "bounds" variable will be generated based on the spacing of the centers

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 18-29


Variables
---------

Variable metadata is primarily ingested through the "variables" section. Here, each variable must have at a minimum the :doc:`required attributes <index>`. Furthermore, attributes such as ``dimensions``, ``raw_data_columns``, and ``system_couplet`` should be added where relevant. Additional attributes may optionally be included. 

- ``dimensions``:
   - should be a list of dimension names. For tabular datasets the first dimension should always be "index" and the second should correspond to either a dimension defined in the early "dimensions" section or within a "systems" section (see examples of "systems" below).

- ``raw_data_columns``:
   - should be a list of column names from the source data file that are meant to be combined into a single 2-D variable.

- ``system_couplet``:
   - the "couplet_label" for the specific data variable. In system definitions, couplets are unique source (transmitter) - receiver pairs. Any data variable containing measurements corresponding to an individual couplet should have the attribute ``system_couplet``. 

In this example below, notice that the variables corresponding to the coordinate variables ``z`` and ``t`` in the earlier ``coordinates`` section have additional required attributes.

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 30-114

Systems
-------

Many geophysical methods entail complex system configurations with detailed ancillary data and metadata information. These system data are often critical for accurate inversion and data handling. GSPy adds this information in a standardized structure and located at the Supplementary Leaflet tier beneath corresponding Data Leaf groups. 

.. literalinclude:: ../../_static/template_system_md.yml
   :language: yaml
   :linenos:
   :lineno-match:

See the page on :doc:`Systems <system_md>` for more information.

Parameters
----------

Additional metadata information, such as inversion settings and parameters, can be added as a Supplementary Leaflet group. 

.. literalinclude:: ../../_static/parameters_md.yml
   :language: yaml
   :linenos:
   :lineno-match:

See the page on :doc:`Parameters <parameters_md>` for more information.

