import os
import pvaccess as pva
import numpy as np
import queue
import time
import threading
import signal
import json
import sys

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
        self.control_pvs['TSAbortScan']             = PV(tomoscan_prefix + 'AbortScan')
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
        # Wait 1 second for all PVs to connect
        time.sleep(1)
        self.check_pvs_connected()

        # Configure callbacks on a few PVs
        for epics_pv in ('StartScan', 'AbortScan'):
            self.epics_pvs[epics_pv].add_callback(self.pv_callback)
        # Set some initial PV values
        for epics_pv in ('StartScan', 'AbortScan'):
            self.epics_pvs[epics_pv].put(0)

        # print(self.epics_pvs)
        for epics_pv in ('SleepSelect', ):
            self.epics_pvs[epics_pv].add_callback(self.pv_callback)

        # Start the watchdog timer thread
        thread = threading.Thread(target=self.reset_watchdog, args=(), daemon=True)
        thread.start()

        # log.setup_custom_logger("./scanlib.log")

        # self.epics_pvs['ScanLibStatus'].put('All good!')

    def signal_handler(self, sig, frame):
        """Calls abort_scan when ^C is typed"""
        if sig == signal.SIGINT:
            self.abort_scan()

    def reset_watchdog(self):
        """Sets the watchdog timer to 5 every 3 seconds"""
        while True:
            self.epics_pvs['Watchdog'].put(5)
            time.sleep(3)

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

    def check_pvs_connected(self):
        """Checks whether all EPICS PVs are connected.

        Returns
        -------
        bool
            True if all PVs are connected, otherwise False.
        """

        all_connected = True
        for key in self.epics_pvs:
            if not self.epics_pvs[key].connected:
                log.error('PV %s is not connected', self.epics_pvs[key].pvname)
                all_connected = False
        return all_connected

    def pv_callback(self, pvname=None, value=None, char_value=None, **kw):
        """Callback function that is called by pyEpics when certain EPICS PVs are changed

        The PVs that are handled are:

        - ``StartScan`` : Calls ``run_scan()``

        - ``AbortScan`` : Calls ``abort_scan()``
        """

        log.debug('pv_callback pvName=%s, value=%s, char_value=%s', pvname, value, char_value)
        if (pvname.find('StartScan') != -1) and (value == 1):
            self.run_scans()
        elif (pvname.find('AbortScan') != -1) and (value == 1):
            self.abort_scan()


    def abort_scan(self):
        """Aborts a scan that is running and performs the operations 
        needed when a scan is aborted.

        This does the following:

        - Sets scan_is_running, a flag that is checked in ``wait_camera_done()``.
          If ``wait_camera_done()`` finds the flag set then it raises a 
          ScanAbortError exception.

        - Stops the rotation motor.

        - Stops the file saving plugin.
        """

        self.scan_is_running = False

        # Abort the current scan
        self.control_pvs['TSAbortScan'].put(0)

    def run_scans(self):
        """Runs ``fly_scan()`` in a new thread."""

        thread = threading.Thread(target=self.run_scan, args=())
        thread.start()

    def run_scan(self):
        
        tomoscan_prefix = self.pv_prefixes['Tomoscan']
        sleep_steps = self.epics_pvs['SleepSteps'].get()
        sleep_time  = self.epics_pvs['SleepTime'].get()
        sleep_select  = self.epics_pvs['SleepSelect'].get(as_string=True)
        in_situ_select = self.epics_pvs['InsituSelect'].get(as_string=True)
        in_situ_start = self.epics_pvs['InsituStart'].get()
        in_situ_step_size = self.epics_pvs['InsituStepSize'].get()
        
        scan_type = self.epics_pvs['ScanType'].get(as_string=True) 
        self.epics_pvs['TSScanType'].put(scan_type)
        print(scan_type, ts_scan_type)
        
        if self.epics_pvs['TSServerRunning'].get():
            if self.epics_pvs['TSScanStatus'].get(as_string=True) == 'Scan complete':
                log.warning('%s scan start', scan_type)
                self.epics_pvs['TSScanType'].put(scan_type, wait=True)
                if (sleep_steps >= 1) and (sleep_select == 'Yes'):
                    log.warning('running %d x %2.2fs sleep scans', sleep_steps, sleep_time)
                    tic =  time.time()
                    for ii in np.arange(0, sleep_steps, 1):
                        log.warning('sleep start scan %d/%d', ii, sleep_steps-1)
                        scan(self)
                        if (sleep_steps+1)!=(ii+1):
                            if (in_situ_select == 'Yes'):
                                in_situ_set_value = in_situ_start + (ii) * in_situ_step_size
                                log.error('in-situ set value: %3.3f ', in_situ_set_value)
                                # set in-situ PV
                                # wait on in-situ read back value
                            log.warning('wait (s): %s ' , str(sleep_time))
                            time.sleep(sleep_time)
                    dtime = (time.time() - tic)/60.
                    log.info('sleep scans time: %3.3f minutes', dtime)
                    log.warning('sleep scan end')
                else:
                    scan(args, ts_pvs)
                log.warning('%s scan end', scan_type)
                self.epics_pvs['TSScanType'].put('Single', wait=True)
            else:
                log.error('Server %s is busy. Please run a scan manually first.', tomoscan_prefix)
        else:
            log.error('Server %s is not runnig', tomoscan_prefix)

    def scan(self):

        tic_01 =  time.time()
        flat_field_axis = self.epics_pvs['TSFlatFieldAxis'].get(as_string=True)
        flat_field_mode = self.epics_pvs['TSFlatFieldMode'].get(as_string=True)
        scan_type = self.epics_pvs['ScanType'].get(as_string=True) 

        if (scan_type == 'Single'):
            single_scan(self)
        elif (scan_type == 'File'):
            file_scan(self)   
        elif (scan_type == 'Energy'):
            energy_scan(self)        
        elif (scan_type == 'Mosaic'):
            start_y = self.epics_pvs['VerticalStart'].get()
            step_size_y = self.epics_pvs['VerticalStepSize'].get()  
            steps_y = self.epics_pvs['VerticalSteps'].get()
            end_y = start_y + (step_size_y * steps_y) 

            start_x = self.epics_pvs['HorizontalStart'].get()
            step_size_x = self.epics_pvs['HorizontalStepSize'].get()
            steps_x = self.epics_pvs['HorizontalSteps'].get()  
            end_x = start_x + (step_size_x * steps_x)

            log.info('vertical positions (mm): %s', np.linspace(start_y, end_y, steps_y, endpoint=False))
            for i in np.linspace(start_y, end_y, steps_y, endpoint=False):
                log.warning('%s stage start position: %3.3f mm', 'SampleInY', i)
                if flat_field_axis in ('X') or flat_field_mode == 'None':
                    pv_y = "TSSampleY"
                else:
                    pv_y = "TSSampleInY"
                self.epics_pvs[pv_y].put(i, wait=True)
                log.info('horizontal positions (mm): %s', np.linspace(start_x, end_x, steps_x, endpoint=False))
                for j in np.linspace(start_x, end_x, steps_x, endpoint=False):
                    log.warning('%s stage start position: %3.3f mm', 'SampleInX', j)
                    if flat_field_axis in ('Y') or flat_field_mode == 'None':
                        pv_x = "TSSampleX"
                    else:
                        pv_x = "TSSampleInX"
                    self.epics_pvs[pv_x].put(j, wait=True, timeout=600)
                    single_scan(args, ts)
            dtime = (time.time() - tic_01)/60.
            log.info('%s scan time: %3.3f minutes', scan_type, dtime)
        else:
            if (scan_type == 'Horizontal'):
                start = self.epics_pvs['HorizontalStart'].get()
                step_size = self.epics_pvs['HorizontalStepSize'].get()       
                steps = self.epics_pvs['HorizontalSteps'].get()
                end = start + (step_size * steps)
                log.info('horizontal positions (mm): %s', np.linspace(start, end, steps, endpoint=False))
                if flat_field_axis in ('Y') or flat_field_mode == 'None':
                    pv = "TSSampleX"
                else:
                    pv = "TSSampleInX"
            elif (scan_type == 'Vertical'):
                start = self.epics_pvs['VerticalStart'].get()
                step_size = self.epics_pvs['VerticalStepSize'].get()
                steps = self.epics_pvs['VerticalSteps'].get()
                end = start + (step_size * steps)
                log.info('vertical positions (mm): %s', np.linspace(start, end, steps, endpoint=False))
                if flat_field_axis in ('X') or flat_field_mode == 'None':
                    pv = "TSSampleY"
                else:
                    pv = "TSSampleInY"
            for i in np.linspace(start, end, steps, endpoint=False):
                log.warning('%s stage start position: %3.3f mm', pv, i)
                self.epics_pvs[pv].put(i, wait=True, timeout=600)
                single_scan(args, ts)
            dtime = (time.time() - tic_01)/60.
            log.info('%s scan time: %3.3f minutes', scan_type, dtime)

        self.epics_pvs['TSScanType'].put('Single', wait=True)

    def single_scan(self):

        testing_select  = self.epics_pvs['TestingSelect'].get(as_string=True)

        tic_01 =  time.time()
        log.info('single scan start')
        if testing_select == 'Yes':
            log.warning('testing mode')
        else: 
            self.epics_pvs['TSStartScan'].put(1, wait=True, timeout=360000) # -1 - no timeout means timeout=0
        dtime = (time.time() - tic_01)/60.
        log.info('single scan time: %3.3f minutes', dtime)

    def energy_scan(self):
        
        tomoscan_prefix = self.pv_prefixes['Tomoscan']
        testing_select  = self.epics_pvs['TestingSelect'].get(as_string=True)

        tic_01 =  time.time()
        log.info('energy scan start')
        
        self.epics_pvs['TSStartEnergyChange'] = PV(tomoscan_prefix + 'StartEnergyChange')    
        self.epics_pvs['TSEnergy'] = PV(tomoscan_prefix + 'Energy')    
        
        # # need to handle file name passing
        # energies = np.load(args.file_energies)    
        
        # # read pvs for 2 energies
        # pvs1, pvs2, vals1, vals2 = [],[],[],[]
        # with open(args.file_params1,'r') as fid:
        #     for pv_val in fid.readlines():
        #         pv, val = pv_val[:-1].split(' ')
        #         pvs1.append(pv)
        #         vals1.append(float(val))
        # with open(args.file_params2,'r') as fid:
        #     for pv_val in fid.readlines():
        #         pv, val = pv_val[:-1].split(' ')
        #         pvs2.append(pv)
        #         vals2.append(float(val))                    
        
        # for k in range(len(pvs1)):
        #     if(pvs1[k]!=pvs2[k]):
        #         log.error("Inconsitent files with PVs")
        #         exit(1)

        # if(np.abs(vals2[0]-vals1[0])<0.001):            
        #     log.error("Energies in params files should be different")
        #     exit(1)

        # # energy scan
        # print(energies)
        # energies=energies/1000.0
        # for energy in energies:               
        #     log.info("energy %.3f eV", energy)                    
        #     # interpolate values
        #     vals = []                     
        #     for k in range(len(pvs1)):
        #         vals.append(vals1[k]+(energy-vals1[0])*(vals2[k]-vals1[k])/(vals2[0]-vals1[0]))               
        #     if testing_select == 'Yes':
        #         log.warning('testing mode')
        #     else:           
        #         # set new pvs  
        #         for k in range(1,len(pvs1)):# skip energy line
        #             if(pvs1[k]=="32idcTXM:mxv:c1:m6.VAL"):
        #                 log.info('old Camera Z %3.3f', PV(pvs1[k]).get())
        #                 PV(pvs1[k]).put(vals[k],wait=True)                                                        
        #                 log.info('new Camera Z %3.3f', PV(pvs1[k]).get())
        #             if(pvs1[k]=="32idcTXM:mcs:c2:m3.VAL"):
        #                 log.info('old FZP Z %3.3f', PV(pvs1[k]).get())
        #                 PV(pvs1[k]).put(vals[k],wait=True)
        #                 log.info('new FZP Z %3.3f', PV(pvs1[k]).get())
        #             if(pvs1[k]=="32idcTXM:mcs:c2:m1.VAL"):
        #                 log.info('old FZP X %3.3f', PV(pvs1[k]).get())
        #                 PV(pvs1[k]).put(vals[k],wait=True)
        #                 log.info('new FZP X %3.3f', PV(pvs1[k]).get())
                                        
        #         # set new energy
        #         self.epics_pvs['TSEnergy'].put(energy)
        #         time.sleep(1)
        #         # change energy via tomoscan
        #         self.epics_pvs['TSStartEnergyChange'].put(1)#,timeout=3600)
        #         log.warning('wait 10s to finalize energy changes')
        #         time.sleep(10)
        #         log.warning('start scan')
        #         # start scan
        #         self.epics_pvs['TSStartScan'].put(1, wait=True, timeout=360000) # -1 - no timeout means timeout=0                
                
        # dtime = (time.time() - tic_01)/60.
        # log.info('energy scan time: %3.3f minutes', dtime)
        # self.epics_pvs['TSScanType'].put('Single', wait=True)


    def file_scan(args, ts):

        tic_01 =  time.time()
        log.info('file scan start')
        # # need to handle file name passing
        # try:
        #     with open(args.scan_file) as json_file:
        #         scan_dict = json.load(json_file)
        # except FileNotFoundError:
        #     log.error('File %s not found', args.scan_file)
        #     exit()
        # except:
        #     log.error('File %s is not correcly formatted', args.scan_file)
        #     exit()
        # flat_field_axis = self.epics_pvs['TSFlatFieldAxis'].get(as_string=True)
        # flat_field_mode = self.epics_pvs['TSFlatFieldMode'].get(as_string=True)

        # for key, value in scan_dict.items():


        #     self.epics_pvs['TSSampleX'].put(value['SampleX'], wait=True)
        #     self.epics_pvs['TSSampleY'].put(value['SampleY'], wait=True)
        #     self.epics_pvs['TSRotationStart'].put(value['RotationStart'], wait=True) 
        #     self.epics_pvs['TSRotationStep'].put(value['RotationStep'], wait=True)
        #     self.epics_pvs['TSNumAngles'].put(value['NumAngles'], wait=True) 
        #     self.epics_pvs['TSReturnRotation'].put(value['ReturnRotation'], wait=True) 
        #     self.epics_pvs['TSNumDarkFields'].put(value['NumDarkFields'], wait=True) 
        #     self.epics_pvs['TSDarkFieldMode'].put(value['DarkFieldMode'], wait=True) 
        #     self.epics_pvs['TSDarkFieldValue'].put(value['DarkFieldValue'], wait=True) 
        #     self.epics_pvs['TSNumFlatFields'].put(value['NumFlatFields'], wait=True) 
        #     self.epics_pvs['TSFlatFieldAxis'].put(value['FlatFieldAxis'], wait=True) 
        #     self.epics_pvs['TSFlatFieldMode'].put(value['FlatFieldMode'], wait=True) 
        #     self.epics_pvs['TSFlatFieldValue'].put(value['FlatFieldValue'], wait=True) 
        #     self.epics_pvs['TSFlatExposureTime'].put(value['FlatExposureTime'], wait=True) 
        #     self.epics_pvs['TSDifferentFlatExposure'].put(value['DifferentFlatExposure'], wait=True) 
        #     self.epics_pvs['TSSampleInX'].put(value['SampleInX'], wait=True) 
        #     self.epics_pvs['TSSampleOutX'].put(value['SampleOutX'], wait=True) 
        #     self.epics_pvs['TSSampleInY'].put(value['SampleInY'], wait=True) 
        #     self.epics_pvs['TSSampleOutY'].put(value['SampleOutY'], wait=True) 
        #     self.epics_pvs['TSSampleOutAngleEnable'].put(value['SampleOutAngleEnable'], wait=True) 
        #     self.epics_pvs['TSSampleOutAngle'].put(value['SampleOutAngle'], wait=True) 
        #     self.epics_pvs['TSScanType'].put(value['ScanType'], wait=True) 
        #     self.epics_pvs['TSFlipStitch'].put(value['FlipStitch'], wait=True) 
        #     self.epics_pvs['TSExposureTime'].put(value['ExposureTime'], wait=True)

        #     log.warning('Scan key/number: %s ', key)
        #     log.warning('%s stage position: %3.3f mm', 'Sample Y', value['SampleY'])
        #     log.warning('%s stage position: %3.3f mm', 'Sample X', value['SampleX'])
        #     if flat_field_axis in ('X') or flat_field_mode == 'None':
        #         pv_y = "TSSampleY"
        #     else:
        #         pv_y = "TSSampleInY"
        #     self.epics_pvs[pv_y].put(value['SampleY'], wait=True)
        #     if flat_field_axis in ('Y') or flat_field_mode == 'None':
        #         pv_x = "TSSampleX"
        #     else:
        #         pv_x = "TSSampleInX"
        #     self.epics_pvs[pv_x].put(value['SampleX'], wait=True, timeout=600)
        #     # single_scan(args, ts)
        #     # config.write(args.config, args, sections=config.SINGLE_SCAN_PARAMS)

        # dtime = (time.time() - tic_01)/60.
        # log.info('file scan time: %3.3f minutes', dtime)
        # self.epics_pvs['TSScanType'].put('Single', wait=True)

