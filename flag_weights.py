#! /usr/bin/python
"""
Flag visibilities with weights below the provided threshold.

Usage: flag_weights.py msdata threshold
Options:
    msdata : str          MS data set containing the data to be flagged.
    threshold : float     Visibilities with a weight below the specified
                          value will be flagged. Must be positive.

Version: 1.3
Date: Apr 2018
Written by Benito Marcote (marcote@jive.eu)

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
    parser.add_argument('--version', action='version', version='%(prog)s 1.3')
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
    weights = ms.getcol("WEIGHT")
    print('Got {0:9} weights'.format(weights.size))
    indexes = np.where(weights < threshold)
    indexes2 = np.where((weights < threshold) & (weights > 0.0))
    print('Got {0:9} bad points'.format(indexes[0].size))
    print('{0:04.3}% of the total visibilities to flag\n'.format(100.0*indexes[0].size/weights.size))
    print('{0:04.3}% of actual data (non-zero) to flag\n'.format(100.0*indexes2[0].size/weights.size))
    if verbose:
        weights[indexes] = -np.abs(weights[indexes])
        ms.putcol("WEIGHT", weights)
        print('Done.')
    else:
        rint('Flag has not been applied.')

    ms.close()


