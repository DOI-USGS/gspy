#######
Systems
#######

The GS standard provides a dedicated location and framework for describing geophysical systems. To apply to the wide variety of geophysical methods, techniques, and instruments, the GS standard defines a system as a composition of four elements:

1. **sources or transmitters (TX)** - sends energy into the earth
2. **receivers (RX)** - record natural or induced signals from the earth
3. **couplets** - represent one or more specific transmitter-receiver combinations 
4. **channels** - represent discrete values recorded by a receiver. Channels typically match a data variable dimension, but are flexible in their composition from sources, receivers, and couplets. For example, a data variable may have channels associated with a single couplet, or channels that result from the combination of multiple couplets.

Systems are passed through metadata files, either with the Survey or Data Leaf metadata files. When included in the Survey file, systems are added directly beneath it temporarily for use in constructing the Data Tree (e.g. systems can be passed directly from the /survey when adding new datasets). However, when writing to netCDF, all systems attached directly to the '/survey' group are dropped and only those at the System Leaflet tier (benath Data Leaves) are retained.  

Below is an example of a dual-moment electromagnetic (EM) time-domain system. In this case, the data channel corresponds to the dimensions of high and low moment gate times.

.. important::
   Systems expect the sections "transmitter", "receiver", and "couplet" underneath the "variables" header. Any ``key: value`` pairs beneath these headers should represent properties and metadata information pertaining to just that element of the system, and will automatically have that header prefixed to the variable names. For example, "area" under "transmitter" will become the variable "transmitter_area". 

   The ``label`` field beneath each "transmitter" and "receiver" is required and used to define both the dimensions of their variables and the labels of the "couplet". By default, GSPy generates the variable ``couplet_label`` by combining the transmitter and receiver labels: {transmitter_label}_{receiver_label}. Users can override this by explicitly passing a "label" field beneath the "couplet" header. In either case, the ``system_couplet`` attributes underneath data variables in the Data Leaf group must match!

.. literalinclude:: ../../_static/template_system_md.yml
   :language: yaml
   :linenos:
   :lineno-match: 
   :lines: 1-145

Below is an example of a simple scalar magnetometer system. There is no concept of a channel dimension in this case. However this example demonstrates how additional prefixes for categories within the system, like "base_magnetometer", are passed through the "prefixes" key. Under "variables" that prefix should be a header at the same indent level as "transmitter", "receiver", and "couplet". Any ``key: value`` pairs indented beneath it become variables with that prefix in the name. 

.. literalinclude:: ../../_static/template_system_md.yml
   :language: yaml
   :linenos:
   :lineno-match: 
   :lines: 147-224

.. note::
   Variables within the System Leaflet groups do NOT require the same variable metadata that Data Leaf variables require (e.g. ``standard_name`` and ``long_name``). However attributes such as ``units`` can optionally be passed where deemed appropriate, and ``dimensions`` may still be needed.
