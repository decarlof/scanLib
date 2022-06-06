# This script creates an object of type ScanLib for supporting scanLibApp
# To run this script type the following:
#     python -i start_scanlib.py
# The -i is needed to keep Python running, otherwise it will create the object and exit
from scanlib.scanlib import ScanLib
ts = ScanLib(["../../db/scanLib_settings.req","../../db/scanLib_settings.req"], {"$(P)":"32id:", "$(R)":"ScanLib:"})
