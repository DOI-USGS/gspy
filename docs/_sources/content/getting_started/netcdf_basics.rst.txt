*************
NetCDF Basics
*************

Here we summarize the central components of netCDF files and clarify the terminology used by GSPy.

In a netCDF file, each group is an individual dataset. The terms “group” and “dataset” are used interchangeably. Groups are arranged like directories in a file system, e.g., /groupA/groupB/groupC. 

Each group is composed of three basic elements: **dimensions**, **variables**, and **attributes**. There is a further distinction of **coordinate variables** as a specific type of data variable (called “coordinates” hereafter). Each variable within a dataset has its own dimensions, coordinates, and attributes. The dimensions and coordinates from each variable are available to the dataset, in this way the dimensions and coordinates of the dataset reflect all dimensions and coordinates from all variables contained within the dataset. Conversely, variable attributes remain specific to their variables and are distinct from the attributes of the dataset. 

Group Attributes
~~~~~~~~~~~~~~~~

At the group level, attributes are attached for required and supplemental metadata information. Attributes are always ``key: value`` pairs, and the value can be a string, a scalar value, or a one-dimensional list. 

See the :doc:`Metadata <../metadata/index>` documentation for more details on required group attributes.

Coordinates
~~~~~~~~~~~

Coordinates serve to locate data values in time, space, or as a function of any other non-spatiotemporal coordinate. Any variable with a spatiotemporal dimension must have a corresponding coordinate variable (e.g., latitude, longitude, elevation, and time). 

Coordinate variables that pertain to the dimensions of data variables are termed **dimension coordinates**. Coordinate variables that do not define dimensions are also permissible and are termed **auxiliary coordinates**. 

The CF conventions treat four types of coordinates with particular control: longitude (or easting), latitude (or northing), vertical, and time. GSPy standardizes these names as simply: 

    * ``x``
    * ``y``
    * ``z``
    * ``t``
    
These four coordinates have specific attributes and standard names required for maximum interoperability with software and routines that ingest and display spatiotemporal data. See the :doc:`Metadata <../metadata/index>` pages for those details.

A GS-standard file should have no more than one of each of these spatiotemporal coordinates per group. 

The GS standard follows CF conventions in defining a special coordinate variable for the coordinate reference system (CRS) of the data, and goes further by standardizing the name as "spatial_ref". GSPy will create the complete ``spatial_ref`` variable using minimal :doc:`user input <../metadata/survey_md>`.

Dimensions
~~~~~~~~~~

Dimensions are scalar values that define the axes of the data variables and may represent a real physical dimension in space or time, or a non-physical dimension such as an index or station name. A dimension is simply a name and a length. When the dimension of the data is also represented by a coordinate variable, that variable becomes a **dimension coordinate**. 

Variables
~~~~~~~~~

Variables are the basic unit of named data in a netCDF dataset. Variables consist of an n-dimensional array of values sharing the same data type and meaning. The shape of a variable is defined by dimensions, and the locations along those dimensions may be assigned coordinates through a coordinate variable. 

Variables Attributes
~~~~~~~~~~~~~~~~~~~~

Each individual data variable is assigned variable-specific metadata through  attributes. At a minimum, ``standard_name``, ``long_name``, and ``units`` are required for all variables, and those with numeric values also need ``_FillValue`` and ``valid_range`` to document missing and null values. Additional metadata information pertaining to specific variables may optionally be attached with no restrictions. 

See the :doc:`Metadata <../metadata/index>` documentation for more details on required variable attributes.