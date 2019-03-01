#!/usr/bin/env python3
"""
Flag visibilities with weights below the provided threshold.

Usage: flag_weights.py msdata threshold
Options:
    msdata : str          MS data set containing the data to be flagged.
    threshold : float     Visibilities with a weight below the specified
                          value will be flagged. Must be positive.

Version: 2.0
Date: Mar 2019
Written by Benito Marcote (marcote@jive.eu)

version 2.0 changes
- Major revision. Now it does not modify the weights anymore. Instead, it
  flags those data with weights below the given threshold by modifying the
  FLAG table.
- Small change in print messages to show '100%' instead of '1e+02%' in certain
  cases.
version 1.4 changes
- Now it also reports the percentage or data that were different from
  zero and will be flagged (not only the total data as before).
version 1.3 changes
- Minor fixes (prog name in optparse info).
version 1.2 changes
- Minor fixes.
version 1.1 changes
- Added option -v that allows you to just get how many visibilities will
  be flagged (but without actually flagging the data).

"""

from pyrap import tables as pt
import numpy as np
import sys


help_msdata = 'Measurement set containing the data to be corrected.'
help_threshold = 'Visibilities with a weight below this value will be flagged. Must be positive.'
help_v = 'Only checks the visibilities to flag (do not flag the data).'

try:
    usage = "%(prog)s [-h] <measurement set> <weight threshold>"
    description="""Flag visibilities with weights below the provided threshold.
    """
    import argparse
    parser = argparse.ArgumentParser(description=description, prog='flag_weights.py', usage=usage)
    parser.add_argument('msdata', type=str, help=help_msdata)
    parser.add_argument('threshold', type=float, help=help_threshold)
    parser.add_argument('--version', action='version', version='%(prog)s 1.4')
    parser.add_argument("-v", "--verbose", default=True, action="store_false" , help=help_v)
    arguments = parser.parse_args()
    #print('The arguments ', arguments)
    verbose = arguments.verbose
    msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata
    threshold = arguments.threshold
except ImportError:
    usage = "%prog [-h] [-v] <measurement set> <weight threshold>"
    description="""Flag visibilities with weights below the provided threshold.
    """
    # Compatibility with Python 2.7 in eee
    import optparse
    parser = optparse.OptionParser(usage=usage, description=description, prog='flag_weights.py', version='%prog 1.3')
    parser.add_option("-v", action="store_false", dest="verbose", default=True, help=help_v)
    theparser = parser.parse_args()
    verbose = theparser[0].verbose
    arguments = theparser[1]
    #arguments = parser.parse_args()[1]
    if len(arguments) != 2:
        print('Two arguments must be provided: flag_weights.py [-h] [-v] <measurement set> <weight threshold>')
        print('Use -h to get help.')
        sys.exit(1)

    msdata = arguments[0][:-1] if arguments[0][-1]=='/' else arguments[0]
    threshold = float(arguments[1])


assert threshold > 0.0

with pt.table(msdata, readonly=False, ack=False) as ms:
    flag_table = ms.getcol("FLAG")
    if 'WEIGHT_SPECTRUM' in ms.colnames():
        # WEIGHT_SPECTRUM has the same shape as FLAG: rows x channels x pol
        w_spectrum = ms.getcol("WEIGHT_SPECTRUM")
        assert flag_table.shape == w_spectrum.shape
        indexes = np.where(ws_spectrum < threshold)
        indexes2 = np.where((ws_spectrum < threshold) & (ws_spectrum > 0.0))
        print('Got {0:9} bad points'.format(indexes[0].size))
        print('{0:04.4}% of the total visibilities to flag'.format(100.0*indexes[0].size/w_spectrum.size))
        print('{0:04.4}% of actual data (non-zero) to flag\n'.format(100.0*indexes2[0].size/w_spectrum.size))
        if verbose:
            flag_table[indexes] = True
            ms.putcol("FLAG", flag_table)
            print('Done.')
        else:
            print('Flags have not been applied.')

    else:
        # WEIGHT does NOT have the same shape as FLAG: rows x pol VERSUS rows x channels x pol
        weights = ms.getcol("WEIGHT")
        assert flag_table[:,1,:].shape == weights.shape
        print('Got {0:9} weights'.format(weights.size))
        indexes = np.where(weights < threshold)
        indexes2 = np.where((weights < threshold) & (weights > 0.0))
        print('Got {0:9} bad points'.format(indexes[0].size))
        print('{0:04.4}% of the total visibilities to flag'.format(100.0*indexes[0].size/weights.size))
        print('{0:04.4}% of actual data (non-zero) to flag\n'.format(100.0*indexes2[0].size/weights.size))
        if verbose:
            n_channels = flag_table.shape[1]
            for a_chan in range(n_channels):
                flag_table[:,a_chan,:][indexes] = True

            ms.putcol("FLAG", flag_table)
            print('Done.')
        else:
            print('Flags have not been applied.')

    ms.close()


