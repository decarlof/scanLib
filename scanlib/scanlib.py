import os
import pvaccess as pva
import numpy as np
import queue
import time
import threading
import signal
import json

from pathlib import Path
from scanlib import util
from scanlib import log
from epics import PV


class ScanLib():
    """ Class for controlling TXM optics via EPICS

        Parameters
        ----------
        args : dict
            Dictionary of pv variables.
    """

    def __init__(self, pv_files, macros):

        # init pvs
        self.scan_is_running = False
        self.config_pvs = {}
        self.control_pvs = {}
        self.pv_prefixes = {}
        
        if not isinstance(pv_files, list):
            pv_files = [pv_files]
        for pv_file in pv_files:
            self.read_pv_file(pv_file, macros)

        if 'SampleX' not in self.control_pvs:
            log.error('SampleXPVName must be present in autoSettingsFile')
            sys.exit()
        if 'SampleY' not in self.control_pvs:
            log.error('SampleYPVName must be present in autoSettingsFile')
            sys.exit()
        if 'Tomoscan' not in self.pv_prefixes:
            log.error('TomoscanPVPrefix must be present in autoSettingsFile')
            sys.exit()

        self.show_pvs()

        # Define PVs from the tomoScan IOC that we will need
        tomoscan_prefix = self.pv_prefixes['Tomoscan']

        sample_x_pv_name                            = PV(tomoscan_prefix + 'SampleXPVName').value
        sample_y_pv_name                            = PV(tomoscan_prefix + 'SampleYPVName').value
        self.control_pvs['TSSampleX']               = PV(sample_x_pv_name)
        self.control_pvs['TSSSampleY']              = PV(sample_y_pv_name)
        self.control_pvs['TSStartScan']             = PV(tomoscan_prefix + 'StartScan')
        self.control_pvs['TSServerRunning']         = PV(tomoscan_prefix + 'ServerRunning')
        self.control_pvs['TSScanStatus']            = PV(tomoscan_prefix + 'ScanStatus')
        self.control_pvs['TSSampleName']            = PV(tomoscan_prefix + 'SampleName')
        self.control_pvs['TSRotationStart']         = PV(tomoscan_prefix + 'RotationStart')  
        self.control_pvs['TSRotationStep']          = PV(tomoscan_prefix + 'RotationStep')  
        self.control_pvs['TSNumAngles']             = PV(tomoscan_prefix + 'NumAngles')  
        self.control_pvs['TSReturnRotation']        = PV(tomoscan_prefix + 'ReturnRotation')  
        self.control_pvs['TSNumDarkFields']         = PV(tomoscan_prefix + 'NumDarkFields')  
        self.control_pvs['TSDarkFieldMode']         = PV(tomoscan_prefix + 'DarkFieldMode')  
        self.control_pvs['TSDarkFieldValue']        = PV(tomoscan_prefix + 'DarkFieldValue')  
        self.control_pvs['TSNumFlatFields']         = PV(tomoscan_prefix + 'NumFlatFields')
        self.control_pvs['TSFlatFieldAxis']         = PV(tomoscan_prefix + 'FlatFieldAxis')
        self.control_pvs['TSFlatFieldMode']         = PV(tomoscan_prefix + 'FlatFieldMode')
        self.control_pvs['TSFlatFieldValue']        = PV(tomoscan_prefix + 'FlatFieldValue')  
        self.control_pvs['TSFlatExposureTime']      = PV(tomoscan_prefix + 'FlatExposureTime')  
        self.control_pvs['TSDifferentFlatExposure'] = PV(tomoscan_prefix + 'DifferentFlatExposure')
        self.control_pvs['TSSampleInX']             = PV(tomoscan_prefix + 'SampleInX')
        self.control_pvs['TSSampleOutX']            = PV(tomoscan_prefix + 'SampleOutX')  
        self.control_pvs['TSSampleInY']             = PV(tomoscan_prefix + 'SampleInY')
        self.control_pvs['TSSampleOutY']            = PV(tomoscan_prefix + 'SampleOutY')  
        self.control_pvs['TSSampleOutAngleEnable']  = PV(tomoscan_prefix + 'SampleOutAngleEnable') 
        self.control_pvs['TSSampleOutAngle']        = PV(tomoscan_prefix + 'SampleOutAngle')  
        self.control_pvs['TSScanType']              = PV(tomoscan_prefix + 'ScanType')
        self.control_pvs['TSFlipStitch']            = PV(tomoscan_prefix + 'FlipStitch')
        self.control_pvs['TSExposureTime']          = PV(tomoscan_prefix + 'ExposureTime')

        self.epics_pvs = {**self.config_pvs, **self.control_pvs}
        
        # print(self.epics_pvs)
        for epics_pv in ('YesNoSelect', ):
            self.epics_pvs[epics_pv].add_callback(self.pv_callback)

        # Start the watchdog timer thread
        thread = threading.Thread(target=self.reset_watchdog, args=(), daemon=True)
        thread.start()

        log.setup_custom_logger("./scanlib.log")

        self.epics_pvs['ScanLibStatus'].put('All good!')

    def reset_watchdog(self):
        """Sets the watchdog timer to 5 every 3 seconds"""
        while True:
            self.epics_pvs['Watchdog'].put(5)
            time.sleep(3)

        log.setup_custom_logger("./scanlib.log")

    def read_pv_file(self, pv_file_name, macros):
        """Reads a file containing a list of EPICS PVs to be used by ScanLib.


        Parameters
        ----------
        pv_file_name : str
          Name of the file to read
        macros: dict
          Dictionary of macro substitution to perform when reading the file
        """

        pv_file = open(pv_file_name)
        lines = pv_file.read()
        pv_file.close()
        lines = lines.splitlines()
        for line in lines:
            is_config_pv = True
            if line.find('#controlPV') != -1:
                line = line.replace('#controlPV', '')
                is_config_pv = False
            line = line.lstrip()
            # Skip lines starting with #
            if line.startswith('#'):
                continue
            # Skip blank lines
            if line == '':
                continue
            pvname = line
            # Do macro substitution on the pvName
            for key in macros:
                pvname = pvname.replace(key, macros[key])
            # Replace macros in dictionary key with nothing
            dictentry = line
            for key in macros:
                dictentry = dictentry.replace(key, '')

            epics_pv = PV(pvname)

            if is_config_pv:
                self.config_pvs[dictentry] = epics_pv
            else:
                self.control_pvs[dictentry] = epics_pv
            # if dictentry.find('PVAPName') != -1:
            #     pvname = epics_pv.value
            #     key = dictentry.replace('PVAPName', '')
            #     self.control_pvs[key] = PV(pvname)
            if dictentry.find('PVName') != -1:
                pvname = epics_pv.value
                key = dictentry.replace('PVName', '')
                self.control_pvs[key] = PV(pvname)
            if dictentry.find('PVPrefix') != -1:
                pvprefix = epics_pv.value
                key = dictentry.replace('PVPrefix', '')
                self.pv_prefixes[key] = pvprefix

    def show_pvs(self):
        """Prints the current values of all EPICS PVs in use.

        The values are printed in three sections:

        - config_pvs : The PVs that are part of the scan configuration and
          are saved by save_configuration()

        - control_pvs : The PVs that are used for EPICS control and status,
          but are not saved by save_configuration()

        - pv_prefixes : The prefixes for PVs that are used for the areaDetector camera,
          file plugin, etc.
        """

        print('configPVS:')
        for config_pv in self.config_pvs:
            print(config_pv, ':', self.config_pvs[config_pv].get(as_string=True))

        print('')
        print('controlPVS:')
        for control_pv in self.control_pvs:
            print(control_pv, ':', self.control_pvs[control_pv].get(as_string=True))

        print('')
        print('pv_prefixes:')
        for pv_prefix in self.pv_prefixes:
            print(pv_prefix, ':', self.pv_prefixes[pv_prefix])

    def pv_callback(self, pvname=None, value=None, char_value=None, **kw):
        """Callback function that is called by pyEpics when certain EPICS PVs are changed
        """

        log.debug('pv_callback pvName=%s, value=%s, char_value=%s', pvname, value, char_value)
        if (pvname.find('YesNoSelect') != -1) and ((value == 0) or (value == 1)):
            thread = threading.Thread(target=self.yes_no_select, args=())
            thread.start()

    def yes_no_select(self):
        """Plot the cross in imageJ.
        """
        print('call back!')
        # if (self.epics_pvs['YesNoSelect'].get() == 0):
        #     sim_epics_pv2_value = self.epics_pvs['scanLibPv2'].get()
        #     self.epics_pvs['scanLibPv1'].put('Hello World!')
        #     self.epics_pvs['scanLibPv2'].put(sim_epics_pv2_value/2.0)
        #     log.info('Yes/No set at %f' % sim_epics_pv2_value)
        #     self.epics_pvs['ScanLibStatus'].put('divide by 2 scanLibPv2')
        # else:
        #     sim_epics_pv2_value = self.epics_pvs['scanLibPv2'].get()
        #     self.epics_pvs['scanLibPv1'].put('Hello APS!')
        #     self.epics_pvs['scanLibPv2'].put(sim_epics_pv2_value*2.0)
        #     log.info('Yes/No set at %f' % sim_epics_pv2_value)
        #     self.epics_pvs['ScanLibStatus'].put('multiply by 2 scanLibPv2')
