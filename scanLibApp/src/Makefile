TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS BELOW HERE

# Build the IOC application
PROD_IOC = scanLibApp

# scanLibApp.dbd will be created and installed
DBD += scanLibApp.dbd

# test.dbd will include these files:
scanLibApp_DBD += base.dbd
scanLibApp_DBD += busySupport.dbd
scanLibApp_DBD += asSupport.dbd

# scanLibApp_registerRecordDeviceDriver.cpp derives from test.dbd
scanLibApp_SRCS += scanLibApp_registerRecordDeviceDriver.cpp

# Build the main IOC entry point where needed
scanLibApp_SRCS_DEFAULT += scanLibMain.cpp
scanLibApp_SRCS_vxWorks += -nil-

scanLibApp_LIBS += autosave
scanLibApp_LIBS += busy
#scanLibApp_LIBS += asyn

# Finally link IOC to the EPICS Base libraries
scanLibApp_LIBS += $(EPICS_BASE_IOC_LIBS)

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD EXTRA GNUMAKE RULES BELOW HERE
