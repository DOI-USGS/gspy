**************************
GS Convention Requirements
**************************

Group structure
---------------

  .. figure:: img/gs_convention.png
      :alt: some image
      :width: 600

      GS data convention. (A) Datasets are structured into three fundamental group types based on content and data geometry. The Survey group contains general metadata about the dataset. Unstructured datasets, such as from CSV or TXT files, form Tabular groups, whereas structured (gridded) datasets are categorized under the Raster group. Metadata is attached to all groups, with various required attributes (green text) that expands on the CF-1.8 convention. (B) Groups follow a strict hierarchy in the NetCDF file, with a single Survey group at the top to which all data groups are attached. Datasets are indexed within their respective group type. (C) Tabular and Raster data groups must contain clearly defined dimensions, such as index or x, y, z, as well as coordinate variables. Raster groups are distinct in that dimensions are also coordinates, whereas Tabular datasets are assigned spatial coordinates that align with the index dimension. Lastly, the coordinate variable “spatial_ref” is required for all data groups, which expands on the “coordinate_information” variable required in the Survey metadata. 


Attributes
----------

+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| Dataset Attributes                                                                                                                                    |
+=====================+=============================================+===================================================================================+
| **attribute name**  | **description**                             | **example**                                                                       |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| title*              | label for the data                          | Example Resolve Airborne Electromagnetic (AEM) Raw Data                           |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| institution*        | who generated the data                      | USGS Geology, Geophysics, & Geochemistry Science Center                           |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| source*             | where the original data came from           | Comma-separated text file                                                         |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| history*            | steps taken to generate release             | processed on 01-01-2022                                                           |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| references*         | Citation to data release                    | Minsley, et al. (2022). doi:https://doi.org/10.5066/P93SY9LI                      |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| content*            | what is in the netcdf file                  | raw data (/survey/tabular/0), processed data (/survey/tabular/1)                  |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| comment             | additional details or ancillary information | raw contractor provided data                                                      |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| summary             | simple summary of the data                  | Airborne electromagnetic (AEM) and magnetic survey data were collected during ... | 
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| created_by          | software version used                       | gspy==0.1.0                                                                       |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
| conventions         | conventions of the data                     | CF-1.8, GS-0.1.0                                                                  |
+---------------------+---------------------------------------------+-----------------------------------------------------------------------------------+
\* required entry


+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variable Attributes                                                                                                                                                              |
+====================+========================================================================+====================================================================================+
| **attribute name** | **description**                                                        | **example**                                                                        |
+--------------------+------------------------------------------------------------------------+------------------------------------------------------------------------------------+
| standard_name*     | name used to identify variable. contains no whitespace, case sensitive | projection_x_coordinate                                                            |
+--------------------+------------------------------------------------------------------------+------------------------------------------------------------------------------------+
| long_name*         | Longer descrition of the variable. Can contain white space.            | Easting, Wisconsin Transverse Mercator (WTM), North American Datum of 1983 (NAD83) |
+--------------------+------------------------------------------------------------------------+------------------------------------------------------------------------------------+
| units*             | units of the variable                                                  | meter                                                                              |
+--------------------+------------------------------------------------------------------------+------------------------------------------------------------------------------------+
| null_value*        | value used for missing data                                            | -9999                                                                              |
+--------------------+------------------------------------------------------------------------+------------------------------------------------------------------------------------+
| valid_range*       | upper and lower bounds this attribute can take                         | [655026.626343047, 732295.562636796]                                               |
+--------------------+------------------------------------------------------------------------+------------------------------------------------------------------------------------+
\* required entry