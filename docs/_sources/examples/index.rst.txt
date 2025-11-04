:orphan:

########
Examples
########


.. raw:: html

    <div class="sphx-glr-thumbnails">

.. thumbnail-parent-div-open

.. thumbnail-parent-div-close

.. raw:: html

    </div>

=================
Creating GS Files
=================


.. raw:: html

    <div class="sphx-glr-thumbnails">

.. thumbnail-parent-div-open

.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="This example demonstrates the workflow for creating a GS file from the ASEG file format, as well as how to add multiple associated datasets to the Survey (e.g., Tabular and Raster groups). Specifically, this AEM survey contains the following datasets:">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_aseg_tempest_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_aseg_tempest.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">ASEG to NetCDF</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="This example demonstrates how to convert comma-separated values (CSV) data to the GS NetCDF format. Specifically this example includes:">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_csv_resolve_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_csv_resolve.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">CSV to NetCDF</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="In this example, we demonstrates the workflow for creating a GS file from the GeoTIFF (.tif/.tiff) file format. This includes adding individual TIF files as single 2-D variables, as well as how to create a 3-D variable by stacking multiple TIF files along a specified dimension.">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_tifs_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_tifs.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">GeoTIFFs to NetCDF</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="This example shows how GSPy can help when you have a large data file and need to do the tedious task of filling out the variable metadata.">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_help_I_have_no_variable_metadata_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_help_I_have_no_variable_metadata.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Help! I have no metadata</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="Loupe to NetCDF">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_csv_loupe_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_csv_loupe.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Loupe to NetCDF</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="These magnetic data channels were pulled from the Wisconsin Skytem example in this repository">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_csv_magnetics_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_csv_magnetics.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Magnetic Survey</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="This example demonstrates the typical workflow for creating a GS file for an AEM survey in its entirety, i.e., the NetCDF file contains all related datasets together, e.g., raw data, processed data, inverted models, and derivative products. Specifically, this survey contains:">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_csv_skytem_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_csv_skytem.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Multi-dataset Survey</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="Workbench to NetCDF">

.. only:: html

  .. image:: /examples/Creating_GS_Files/images/thumb/sphx_glr_plot_xyz_workbench_to_netcdf_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Creating_GS_Files_plot_xyz_workbench_to_netcdf.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Workbench to NetCDF</div>
    </div>


.. thumbnail-parent-div-close

.. raw:: html

    </div>


.. toctree::
   :hidden:

   /examples/Creating_GS_Files/plot_aseg_tempest
   /examples/Creating_GS_Files/plot_csv_resolve
   /examples/Creating_GS_Files/plot_tifs
   /examples/Creating_GS_Files/help_I_have_no_variable_metadata
   /examples/Creating_GS_Files/plot_csv_loupe
   /examples/Creating_GS_Files/plot_csv_magnetics
   /examples/Creating_GS_Files/plot_csv_skytem
   /examples/Creating_GS_Files/plot_xyz_workbench_to_netcdf

=========================
Interacting With GS Files
=========================


.. raw:: html

    <div class="sphx-glr-thumbnails">

.. thumbnail-parent-div-open

.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="The three primary classes (Survey, Tabular, and Raster) all contain data and metadata within Xarray Datasets. This example demonstrates how to access the xarray object for each class, and methods for exploring the data and metadata.">

.. only:: html

  .. image:: /examples/Interacting_With_GS_Files/images/thumb/sphx_glr_plot_xarray_methods_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Interacting_With_GS_Files_plot_xarray_methods.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Basic Class Structure</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="Every Survey must have a coordinate reference system (CRS) defined and all datasets within the Survey adhere to the same CRS.">

.. only:: html

  .. image:: /examples/Interacting_With_GS_Files/images/thumb/sphx_glr_plot_coordinate_reference_systems_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Interacting_With_GS_Files_plot_coordinate_reference_systems.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Coordinate Reference Systems</div>
    </div>


.. raw:: html

    <div class="sphx-glr-thumbcontainer" tooltip="Plotting Cross Sections">

.. only:: html

  .. image:: /examples/Interacting_With_GS_Files/images/thumb/sphx_glr_plot_cross_section_thumb.png
    :alt:

  :ref:`sphx_glr_examples_Interacting_With_GS_Files_plot_cross_section.py`

.. raw:: html

      <div class="sphx-glr-thumbnail-title">Plotting Cross Sections</div>
    </div>


.. thumbnail-parent-div-close

.. raw:: html

    </div>


.. toctree::
   :hidden:

   /examples/Interacting_With_GS_Files/plot_xarray_methods
   /examples/Interacting_With_GS_Files/plot_coordinate_reference_systems
   /examples/Interacting_With_GS_Files/plot_cross_section


.. only:: html

  .. container:: sphx-glr-footer sphx-glr-footer-gallery

    .. container:: sphx-glr-download sphx-glr-download-python

      :download:`Download all examples in Python source code: examples_python.zip </examples/examples_python.zip>`

    .. container:: sphx-glr-download sphx-glr-download-jupyter

      :download:`Download all examples in Jupyter notebooks: examples_jupyter.zip </examples/examples_jupyter.zip>`


.. only:: html

 .. rst-class:: sphx-glr-signature

    `Gallery generated by Sphinx-Gallery <https://sphinx-gallery.github.io>`_
