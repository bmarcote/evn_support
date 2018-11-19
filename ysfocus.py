#! /usr/bin/python
"""
Change the MOUNT field in the ANTENNA table for Ys to 'ALT-AZ-NASMYTH-RH'.
It allows tConvert to put MNTSTA=4 into the FITS AN table, to handle the
parallactic angle correction for Ys's Nasmyth focus correctly.
Also, changes Hobart X_YEW to X-YEW expected by tConvert (MNTSTA=3).

Usage: ysfocus.py <measurement set>

Options:
    msdata : str          MS data set containing the data to be flagged.


Version: 2.0
Date: Jun 2018
Written by Benito Marcote (marcote@jive.eu)


version 2.0 changes
- STATION name is now case insensitive.
- Warns when the STATION already contains the right mount.
- New direct access of the db (put/getcol) to keep the MS locked while running.
  This now also works with referenced MS files.

version 1.2 changes
- Now the script works when the STATION name is also YS or HO (not only
  YEBES40m or HOBART).

"""

from pyrap import tables as pt
import numpy as np
import sys


help_argument = 'Measurement Set containing the data to be corrected.'

try:
    usage = "%(prog)s [-h] <measurement set>"
    description="""Change the MOUNT field in the ANTENNA table for Yebes to 'ALT-AZ-NASMYTH-RH'.
    It allows tConvert to put MNTSTA=4 into the FITS AN table to handle the
    parallactic angle correction for Ys's Nasmyth focus correctly.
    Also, changes Hobart X_YEW to X-YEW expected by tConvert (MNTSTA=3).
    """
    import argparse
    parser = argparse.ArgumentParser(description=description, prog='ysfocus.py', usage=usage)
    parser.add_argument('msdata', type=str, help=help_argument)
    parser.add_argument('--version', action='version', version='%(prog)s 2.0')
    arguments = parser.parse_args()
    # No necessary but it would look better in the output
    msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata
except ImportError:
    usage = "%prog   [-h]  <measurement set>"
    description="""Change the MOUNT field in the ANTENNA table for Ys to 'ALT-AZ-NASMYTH-RH'.
    It allows tConvert to put MNTSTA=4 into the FITS AN table, to handle the
    parallactic angle correction for Ys's Nasmyth focus correctly.
    Also, changes Hobart X_YEW to X-YEW expected by tConvert (MNTSTA=3).
    """
    # Compatibility with Python 2.7 in eee
    import optparse
    parser = optparse.OptionParser(usage=usage, description=description, prog='ysfocus.py', version='%prog 2.0')
    #parser.add_option('measurement_set', type='string', dest='msdata', help=help_doc)
    arguments = parser.parse_args()[1]
    if len(arguments) != 1:
        print('Only one argument is accepted:   ysfocus.py   <measurement set>')
        sys.exit(1)

    # No necessary but it would look better in the output
    msdata = arguments[0][:-1] if arguments[0][-1]=='/' else arguments[0]

# The STATION name can be either the full name or the abreviation
fixed_mounts = {'YEBES40M': 'ALT-AZ-NASMYTH-RH', 'YS': 'ALT-AZ-NASMYTH-RH',
                'HOBART': 'X-YEW', 'HO': 'X-YEW'}



with pt.table(msdata, readonly=False, ack=False) as ms:
    with pt.table(ms.getkeyword('ANTENNA'), readonly=False, ack=False) as ant_table:
        stations = [i.upper() for i in ant_table.getcol('STATION')]
        mounts = ant_table.getcol('MOUNT')
        stations_to_change = set(stations).intersection(fixed_mounts.keys())
        # Function to get directly the position of a station in the array to get its mount
        getmount = lambda station: mounts[stations.index(station)]
        for a_station in stations_to_change:
            if getmount(a_station) == fixed_mounts[a_station]:
                print('{0} has already the right mount ({1})'.format(a_station, fixed_mounts[a_station]))
            else:
                print('Changing {} mount from {} to {}'.format(a_station, getmount(a_station),
                                                               fixed_mounts[a_station]))
                mounts[stations.index(a_station)] = fixed_mounts[a_station]

        # In case no station has been found in the MS
        if len(stations_to_change) == 0:
            print("Neither Ys nor Ho found in the MS, exiting without action")

        ant_table.putcol('MOUNT', mounts)
        # Should not be necessary, but it's casacore, who knows...
        ant_table.flush()

print('\nDone.')

