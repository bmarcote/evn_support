#! /usr/bin/python
"""
Swap polarizations for specified antennas in specified subbands

Usage: polswap.py msdata antennas [-sb SUBBANDS]
Options:
    msdata : str          MS data set containing the data to be swapged.
    antennas : str        Antenna or list of antennas that require to be
                          swapped. Use the two-letter name (e.g. Ef, Mc,
                          or Jb2). In case of more than one station, please
                          use either string 'Ef, Mc' or a non-spaced str:
                          Ef,Mc,Ys.

Version: 0.0a
Date: Dec 2017
Written by Benito Marcote (marcote@jive.eu)
"""

from pyrap import tables as pt
import numpy as np
import sys

# TO CHANGE
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
    parser.add_argument('--version', action='version', version='%(prog)s 1.2')
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
    parser = optparse.OptionParser(usage=usage, description=description, prog='ysfocus.py', version='%prog 1.2')
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

with pt.table(msdata, readonly=False) as ms:
    weights = ms.getcol("WEIGHT")
    print('Got {0:9} weights'.format(weights.size))
    indexes = np.where(weights < threshold)
    print('Got {0:9} bad points'.format(indexes[0].size))
    print('{0:04.3}% of the visibilities to flag\n'.format(100.0*indexes[0].size/weights.size))
    if verbose:
        weights[indexes] = -np.abs(weights[indexes])
        ms.putcol("WEIGHT", weights)
        print('Done.')
    else:
        print('Flag has not been applied')
    ms.close()


