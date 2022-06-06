============================
scanLibApp EPICS application
============================

.. 
   toctree::
   :hidden:

   amcntrols.template
   scanlib_settings.req
   scanlib.substitutions


scanLib includes a complete example of an EPICS application, consisting of:

- A database file and corresponding autosave request file that contain the PVs required by the scanlib.py base class.
- OPI screens for medm
- An example IOC application that can be used to run the above databases.
  The databases are loaded in the IOC with the example substitutions file, 
  :doc:`scanLib.substitutions`.


Base class files
================
The following tables list all of the records in the scanLib.template file.
These records are used by the scanlib base class and so are required.

scanLib.template
----------------

This is the database file that contains only the PVs required by the amcontrol.py base class
:doc:`scanLib.template`.

Camera PV Prefixes
------------------

.. cssclass:: table-bordered table-striped table-hover
.. list-table::
  :header-rows: 1
  :widths: 5 5 90

  * - Record name
    - Record type
    - Description
  * - $(P)$(R)CameraPVPrefix
    - stringout
    - Contains the prefix for the detector, e.g. 2bmbSP2:

Example PV name
---------------

.. cssclass:: table-bordered table-striped table-hover
.. list-table::
  :header-rows: 1
  :widths: 5 5 90

  * - Record name
    - Record type
    - Description
  * - $(P)$(R)ExamplePVName
    - stringout
    - Contains a PV name, e.g. 32id:m1

AM served PVs
^^^^^^^^^^^^^

.. cssclass:: table-bordered table-striped table-hover
.. list-table::
  :header-rows: 1
  :widths: 5 5 90

  * - Record name
    - Record type
    - Description
  * - $(P)$(R)scanLibPv1
    - stringout
    - Contains a string PV.
  * - $(P)$(R)scanLibPv1
    - ao
    - Contains a float PV.
  * - $(P)$(R)scanLibPv1
    - ao
    - Contains a float PV.
  * - $(P)$(R)scanLibPv1
    - ao
    - Contains a float PV.
  * - $(P)$(R)scanLibPv1
    - stringout
    - Contains a string PV.
  * - $(P)$(R)scanLibPv1
    - stringout
    - Contains a string PV.

medm files
----------

scanLib.adl
^^^^^^^^^^^

The following is the MEDM screen :download:`scanLib.adl <../../scanLibApp/op/adl/scanLib.adl>` during a scan. 
The status information is updating.

.. image:: img/scanLib.png
    :width: 75%
    :align: center

scanLibEPICS_PVs.adl
^^^^^^^^^^^^^^^^^^^^

The following is the MEDM screen :download:`scanLibEPICS_PVs.adl <../../scanLibApp/op/adl/scanLibEPICS_PVs.adl>`. 

If these PVs are changed scanLib must be restarted.

.. image:: img/scanLibEPICS_PVs.png
    :width: 75%
    :align: center

