# Convert XDF to NWB

## Python Libraries
The main two libraries needed for conversion are [pynwb](https://pynwb.readthedocs.io/en/stable/index.html) and [pyxdf](https://github.com/xdf-modules/pyxdf)
- pyxdf is used to read the XDF files and extract the data
- pynwb is used to take the data and store it in the NWB file format

## Files

`xdf2nwb.py` is the main file and `xdf2nwb_functions.py` holds many of the core functions required for xdf2nwb to work.

`standardcoordinates.csv` is a look up table usd to find the coordinates of the electrodes for the EEG
