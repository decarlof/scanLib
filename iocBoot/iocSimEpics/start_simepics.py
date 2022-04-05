# This script creates an object of type SimEpics for supporting simEpicsApp
# To run this script type the following:
#     python -i start_simepics.py
# The -i is needed to keep Python running, otherwise it will create the object and exit
from simepics.simepics import SimEpics
ts = SimEpics(["../../db/simEpics_settings.req","../../db/simEpics_settings.req"], {"$(P)":"32id:", "$(R)":"SimEpics:"})
