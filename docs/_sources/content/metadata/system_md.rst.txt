###########
System File
###########

Many geophysical methods entail complex system configurations with detailed ancillary data and metadata information. These system data are often critical for accurate inversion and data handling. 

The GS standard provides a dedicated location and framework for describing geophysical systems. To apply to the wide variety of geophysical methods, techniques, and instruments, the GS standard defines a system as a composition of four elements:

1. **sources or transmitters (TX)** - sends energy into the earth
2. **receivers (RX)** - record natural or induced signals from the earth
3. **couplets** - represent one or more specific transmitter-receiver combinations 
4. **channels** - represent discrete values recorded by a receiver. Channels typically match a data variable dimension, but are flexible in their composition from sources, receivers, and couplets. For example, a data variable may have channels associated with a single couplet, or channels that result from the combination of multiple couplets.


.. literalinclude:: ../../_static/template_system_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
