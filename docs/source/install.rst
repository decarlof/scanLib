==================
Install directions
==================

Build EPICS base
----------------

.. warning:: Make sure the disk partition hosting ~/epics is not larger than 2 TB. See `tech talk <https://epics.anl.gov/tech-talk/2017/msg00046.php>`_ and  `Diamond Data Storage <https://epics.anl.gov/meetings/2012-10/program/1023-A3_Diamond_Data_Storage.pdf>`_ document.

::

    $ mkdir ~/epics
    $ cd epics
    

- Download EPICS base latest release, i.e. 7.0.3.1., from https://github.com/epics-base/epics-base::

    $ git clone https://github.com/epics-base/epics-base.git
    $ cd epics-base
    $ make -sj
    

Build a minimal synApps
-----------------------

To build a minimal synApp::

    $ cd ~/epics

- Download in ~/epics `assemble_synApps <https://github.com/EPICS-synApps/support/blob/master/assemble_synApps.sh>`_.sh
- Edit the assemble_synApps.sh script as follows:
    #. Set FULL_CLONE=True
    #. Set EPICS_BASE to point to the location of EPICS base.  This could be on APSshare (the default), or a local version you built.
    
    For scanlib you need 
    
    #. ASYN=R4-37
    #. AUTOSAVE=R5-10
    #. BUSY=R1-7-2
    #. XXX=R6-1

    You can comment out all of the other modules (ALLENBRADLEY, ALIVE, etc.)

- Run::

    $ assemble_synApps.sh

- This will create a synApps/support directory::

    $ cd synApps/support/

- Edit asyn-RX-YY/configure/RELEASE to comment out the lines starting with::
    
    IPAC=$(SUPPORT)/
    SNCSEQ=$(SUPPORT)/

.. warning:: If building for RedHat8 uncomment **TIRPC=YES** in asyn-RX-YY/configure/CONFIG_SITE


- Clone the scanlib module into synApps/support::
    
    $ git clone https://github.com/tomography/scanlib.git

- Edit configure/RELEASE add this line to the end::
    
    SCANLIB=$(SUPPORT)/scanlib

- Edit Makefile add this line to the end of the MODULE_LIST::
    
    MODULE_LIST += SCANLIB

- Run the following commands::

    $ make release
    $ make -sj

Build the python server
-----------------------

To build the **scanLib** python server you need to have `Conda <https://docs.conda.io/en/latest/miniconda.html>`_
installed.

Next, create a dedicated conda environment for scanLib by running::

    (base) $ conda create --name scanlib python=3.9

then::

    (base) $ conda activate scanlib

and install the required python packages::

    (scanlib) $ pip install pvapy
    (scanlib) $ pip install pyepics

Finally you can build **scanLib** with::

    (scanlib) $ cd ~/epics/synApps/support/scanLib/
    (scanlib) $ python setup.py install

To run the python server::

    (scanlib) $ python -i start_scanlib.py




