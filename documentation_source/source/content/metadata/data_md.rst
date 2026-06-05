##################
Data Metadata File
##################

GSPy uses metadata files (YAML or JSON) to ingest required and ancillary information and build the Data Tree. 

The Data Metadata File contains the following 

Global attributes for the Data group are passed through the dataset attributes, ``dataset_attrs``. The GS standard requires and recommends multiple specific keys, explained on :doc:`this page <index/GS Group Attributes>`.

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 1-10

The four standardized coordinate variables (x, y, z, and t) are specificed through the ``coordinates`` dictionary, which is simply a key mapping to the variables the user wants to designate as the coordinates. 

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 11-17

Tabular vs. Raster Data
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../_static/template_data_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 11-17

must have the attribute “axis” with the values X, Y, Z, or T for universal identification. The vertical (z) and time (t) coordinates also require additional attributes such as `datum`, `positive`.



