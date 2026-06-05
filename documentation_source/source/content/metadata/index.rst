.. _metadata-requirements:

#################
Metadata Handling
#################

GSPy uses metadata files (YAML or JSON) to ingest required and ancillary information and build the GS Data Tree. Information is read from these files into a Metadata dictionary object. When adding a dataset to the GS Data Tree, typically a user would pass a YAML or JSON file, however GSPy has the flexibility to accept a dictionary passed directly as well. 

The contents GSPy expects in the metadata files vary depending on its purpose. See the specific types of metadata linked here for more detail and examples: 

.. toctree::
   :maxdepth: 1

   survey_md
   data_md
   system_md
   parameters_md

Below are summary tables for required attributes per the GS data standard. 

Required Group Attributes
-------------------------

Attributes are attached at both the group (dataset) and variable levels. A set of global attributes is required in the Survey group (see next section) and the GS standard further requires specific attributes for identification and searchability. 

By setting strict requirements on these attributes, the GS Data Tree framework can remain flexible in other areas (i.e., the names and number of groups are free to vary). The required GS attributes ensure all groups within the file can be identified and filtered for efficient data handling. See the example PLACEHOLDER for a demonstration of how to employ group keys to search and filter a GS Data Tree and find specific content. 

Survey
~~~~~~

The ``Survey`` group requires the following fields providing general information about the file and its contents:

+--------------------------+-----------------------------------------------+
| Survey Group Attribute   | Description                                   |
+==========================+===============================================+
| **title**                | A brief description of the dataset collection |
+--------------------------+-----------------------------------------------+
| **history**              | Summarized audit trail for how the data have  |
|                          | been modified and processed                   |
+--------------------------+-----------------------------------------------+
| **institution**          | Who or what organization produced the data    |
+--------------------------+-----------------------------------------------+
| **source**               | How the data or datasets within the file      |
|                          | were produced. If the data where observed,    |
|                          | measured, recorded, or modeled and a brief    |
|                          | description of how                            |
+--------------------------+-----------------------------------------------+
| **comment**              | Miscellaneous information and notes           |
+--------------------------+-----------------------------------------------+
| **references**           | All relevant citations                        |
+--------------------------+-----------------------------------------------+
| **content**              | A list of all groups in the file and what     |
|                          | they contain                                  |
+--------------------------+-----------------------------------------------+
| **conventions**          | The GS and CF convention versions followed    |
+--------------------------+-----------------------------------------------+

GS Group Attributes
~~~~~~~~~~~~~~~~~~~

The GS standard requires additional attributes at the group level based on what Data Tree element the group is (survey root, branch node, data leaf, supplemental stem). 

The attribute ``type`` is required for all groups within a GS file, the value of which is determined by what type of GS Data Tree Element the group represents. The attribute ``structure`` is also required for data leaf groups to capture the geometry of the data, i.e., tabluar is unstructured point data, raster is structured on a rectalinear grid, and mesh is structured on a non-rectalinear grid.

+---------------------------+-------------------+-----------------------+
| GS Data Tree Element      |  **type**         | **structure**         | 
+===========================+===================+=======================+
| **survey root**           | survey            |                       | 
+---------------------------+-------------------+-----------------------+
| **branch nodes**          | container         |                       | 
+---------------------------+-------------------+-----------------------+
| **data leaves**           | data, model       | tabular, raster, mesh | 
+---------------------------+-------------------+-----------------------+
| **supplementary leaflets**| system, parameter |                       | 
+---------------------------+-------------------+-----------------------+

Data Leaves & Supplementary Leaflets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The attributes ``mode``, ``method`` and ``instrument`` are required for the Data Leaves and Supplementary Leaflets but have free (uncontrolled) values. The attribute ``property`` is recommended, when applicable, and is meant to capture the physical or geophysical property being measured or modeled:

+------------------------+---------------------------+------------------------+
| GS Data Tree Element   | required                  | recommended (optional) |
+========================+===========================+========================+
| **data leaves**        |  mode, method, instrument | property               |
+------------------------+---------------------------+------------------------+
| **supplementary stems**|  mode, method, instrument | property               |
+------------------------+---------------------------+------------------------+

The ``mode`` attribute captures the nature of how the data were acquired (e.g., on land, over water, in the air, underground):

+----------------+----------+------------+--------+----------+--------------+
| **mode**       | airborne | waterborne | ground | borehole | ocean bottom |
+----------------+----------+------------+--------+----------+--------------+

Values for the ``method`` field require, at a minimum, one of the primary methods in the table below. Additional submethods can be appended as a comma separated list. If more than one primary method applies, then the method field becomes a 1-D list of values. For example, in increasing complexity: ::

    method: electromagnetic
    method: electromagnetic, time domain
    method: ["electromagnetic, time domain", "magnetic, total field"]

Below are some example ``method`` values with common submethod variants. Values for these fields follows the GS standard guidelines, with lower case text and no abbreviations:

+----------------------------+-----------------------------------+-----------------------+
| **primary method**         | **submethod (A)**                 | **submethod (B)**     |
+============================+===================================+=======================+
| electromagnetic            | frequency domain                  | time domain           |
+----------------------------+-----------------------------------+-----------------------+
| electrical                 | electrical resistivity tomography | induced polarization  |
+----------------------------+-----------------------------------+-----------------------+
| gravity                    | absolute                          | gravity gradiometry   |
+----------------------------+-----------------------------------+-----------------------+
| magnetic                   | total field                       | gradient              |
+----------------------------+-----------------------------------+-----------------------+
| radiometric                | gamma-ray spectrometry            |                       |
+----------------------------+-----------------------------------+-----------------------+
| nuclear                    | neutron                           | natural gamma         |
+----------------------------+-----------------------------------+-----------------------+
| nuclear magnetic resonance |                                   |                       |
+----------------------------+-----------------------------------+-----------------------+
| seismic                    | refraction                        | horizontal-vertical   | 
|                            | tomography                        | spectral ratios       |
+----------------------------+-----------------------------------+-----------------------+

The ``instrument`` attribute contains the name of the instrument used to acquire the data. Here are some examples, and note that captitalization may be necessary here to accurately represent instrument names. This field can also be used to capture serial numbers to convey an individual instrument. For example, if an agency owns multiples of the same instrument it can often be helpful to track data collected from each one in case unqiue behaviors or quirks arise.  

+----------------+-------------+--------------+----------------+--------------+
| **instrument** | SkyTEM 304M | 30Hz TEMPEST | AGI SuperSting | ABEM WalkTEM |         
+----------------+-------------+--------------+----------------+--------------+

The ``property`` attribute is meant to represent the central physical or geophysical property captured by the data:

+--------------+------------------------+-----------------------------+---------+--------------------------+
| **property** | electrical resistivity | residual magnetic intensity | density | volumetric water content | 
+--------------+------------------------+-----------------------------+---------+--------------------------+

Required Variable Attributes
----------------------------

The GS standard requires the following attributes on all variables: 

    * standard_name
    * long_name
    * units
    
All numeric variables require additional attributes to document any null or missing values:
    
    * _FillValue
    * valid_range

+----------------------+----------------------------------------------------------------------------------+
| Variable Attribute   | Description                                                                      |
+======================+==================================================================================+
| **standard_name**    | Succint variable name, containing no whitespace and is case sensitive            |
+----------------------+----------------------------------------------------------------------------------+
| **long_name**        | Descriptive variable name, can have whitespace and is not case sensitive         |
+----------------------+----------------------------------------------------------------------------------+
| **units**            | Measurement system or physical scale of the variable, may also be nondimensional |
+----------------------+----------------------------------------------------------------------------------+
| **_FillValue**       | Value of same type as the variable representing undefined or missing data        |
+----------------------+----------------------------------------------------------------------------------+
| **valid_range**      | Minimum and maximum valid values of the variable                                 |
+----------------------+----------------------------------------------------------------------------------+