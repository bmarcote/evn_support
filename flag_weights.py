#! /usr/bin/python
"""
Flag visibilities with weights below the provided threshold.

Usage: flag_weights.py msdata threshold
Options:
    msdata : str          MS data set containing the data to be flagged.
    threshold : float     Visibilities with a weight below the specified
                          value will be flagged. Must be positive.

Version: 1.0
Date: Oct 2017
Written by Benito Marcote (marcote@jive.eu)
"""

from pyrap import tables as pt
import numpy as np
import sys

                                                                                                             
help_msdata = 'Measurement set containing the data to be corrected.'
help_threshold = 'Visibilities with a weight below this value will be flagged. Must be positive.'

try:
    usage = "%(prog)s [-h] <measurement set> <weight threshold>"
    description="""Flag visibilities with weights below the provided threshold.
    """
    import argparse
    parser = argparse.ArgumentParser(description=description, prog='flag_weights.py', usage=usage)
    parser.add_argument('msdata', type=str, help=help_msdata)
    parser.add_argument('threshold', type=float, help=help_threshold)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    arguments = parser.parse_args()
    print('The arguments ', arguments)
    msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata
    threshold = arguments.threshold
except ImportError:
    usage = "%prog [-h] <measurement set> <weight threshold>"
    description="""Flag visibilities with weights below the provided threshold.
    """
    # Compatibility with Python 2.7 in eee
    import optparse
    parser = optparse.OptionParser(usage=usage, description=description, prog='ysfocus.py', version='%prog 1.0')
    #parser.add_option('measurement_set', type='string', dest='msdata', help=help_doc)
    arguments = parser.parse_args()[1]
    if len(arguments) != 2:
        print('Two arguments must be provided: flag_weights.py <measurement set> <weight threshold>')
        sys.exit(1)

    msdata = arguments[0][:-1] if arguments[0][-1]=='/' else arguments[0]
    threshold = float(arguments[1])


assert threshold > 0.0

with pt.table(msdata, readonly=False) as ms:
    weights = ms.getcol("WEIGHT")
    print('Got {0:9} weights'.format(weights.size))
    indexes = np.where(weights < threshold)
    print('Got {0:9} bad points'.format(indexes[0].size))
    weights[indexes] = -np.abs(weights[indexes])
    ms.putcol("WEIGHT", weights)
    ms.close()


