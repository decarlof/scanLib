TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS BELOW HERE

# Build the IOC application
PROD_IOC = simEpicsApp

# simEpicsApp.dbd will be created and installed
DBD += simEpicsApp.dbd

# test.dbd will include these files:
simEpicsApp_DBD += base.dbd
simEpicsApp_DBD += busySupport.dbd
simEpicsApp_DBD += asSupport.dbd

# simEpicsApp_registerRecordDeviceDriver.cpp derives from test.dbd
simEpicsApp_SRCS += simEpicsApp_registerRecordDeviceDriver.cpp

# Build the main IOC entry point where needed
simEpicsApp_SRCS_DEFAULT += simEpicsMain.cpp
simEpicsApp_SRCS_vxWorks += -nil-

simEpicsApp_LIBS += autosave
simEpicsApp_LIBS += busy
#simEpicsApp_LIBS += asyn

# Finally link IOC to the EPICS Base libraries
simEpicsApp_LIBS += $(EPICS_BASE_IOC_LIBS)

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD EXTRA GNUMAKE RULES BELOW HERE
