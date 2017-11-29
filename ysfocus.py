#! /usr/bin/python
"""
Change the MOUNT field in the ANTENNA table for Ys to 'ALT-AZ-NASMYTH-RH'.
It allows tConvert to put MNTSTA=4 into the FITS AN table, to handle the
parallactic angle correction for Ys's Nasmyth focus correctly.
Also, changes Hobart X_YEW to X-YEW expected by tConvert (MNTSTA=3).

Usage: ysfocus.py <measurement set>

Options:
    msdata : str          MS data set containing the data to be flagged.


Version: 1.0
Date: Oct 2017
Written by Benito Marcote (marcote@jive.eu)
"""

from pyrap import tables as pt
import numpy as np
import sys


help_argument = 'Measurement set containing the data to be corrected.'

try:
    usage = "%(prog)s [-h] measurement_set"
    description="""Change the MOUNT field in the ANTENNA table for Ys to 'ALT-AZ-NASMYTH-RH'.
    It allows tConvert to put MNTSTA=4 into the FITS AN table, to handle the
    parallactic angle correction for Ys's Nasmyth focus correctly.
    Also, changes Hobart X_YEW to X-YEW expected by tConvert (MNTSTA=3).
    """
    import argparse
    parser = argparse.ArgumentParser(description=description, prog='ysfocus.py', usage=usage)
    parser.add_argument('msdata', type=str, help=help_argument)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    arguments = parser.parse_args()
    # No necessary but it would look better in the output
    msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata
except ImportError:
    usage = "%prog [-h] measurement_set"
    description="""Change the MOUNT field in the ANTENNA table for Ys to 'ALT-AZ-NASMYTH-RH'.
    It allows tConvert to put MNTSTA=4 into the FITS AN table, to handle the
    parallactic angle correction for Ys's Nasmyth focus correctly.
    Also, changes Hobart X_YEW to X-YEW expected by tConvert (MNTSTA=3).
    """
    # Compatibility with Python 2.7 in eee
    import optparse
    parser = optparse.OptionParser(usage=usage, description=description, prog='ysfocus.py', version='%prog 1.0')
    #parser.add_option('measurement_set', type='string', dest='msdata', help=help_doc)
    arguments = parser.parse_args()[1]
    if len(arguments) != 1:
        print('Only one argument is accepted: ysfocus.py <measurement set>')
        sys.exit(1)

    # No necessary but it would look better in the output
    msdata = arguments[0][:-1] if arguments[0][-1]=='/' else arguments[0]



stations_to_change = {'YEBES40M': 'ALT-AZ-NASMYTH-RH', 'HOBART': 'X-YEW'}
# I need to check how to do this comparison with TaQL, for now this works
# although it is stupid
with pt.table(msdata+'/ANTENNA') as antenna_table:
    stations = antenna_table.getcol('STATION')
    antenna_table.close()
    n_changes = 0
    # Antennas known to require a change of MOUNT:
    for a_station in stations_to_change:
        if a_station in stations:
            n_changes += 1
            print('Changing {0} mount to {1}'.format(a_station, stations_to_change[a_station]))
            pt.taql("update {0}/ANTENNA set MOUNT='{2}' where STATION == '{1}'".format(msdata,
                                                    a_station, stations_to_change[a_station]))
            print('Done.')

    if n_changes == 0:
        print("Neither Ys nor Ho found in the MS, exiting without action.")



