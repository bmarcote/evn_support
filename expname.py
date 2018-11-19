#! /usr/bin/env python3
"""Change the name of an project in a measurement set (MS).

Usage: expname.py <msdata> <new_expname>

Options:
    msdata : str          MS data set to be changed.
    new_expname : str     New name for the project ( experiment) that is quoted in the MS.
                          It will replace the existing one and it will be converted into
                          capital letters.

Version: 1.0
Date: April 2017
Written by Benito Marcote (marcote@jive.eu)
"""

from pyrap import tables as pt
import sys

help_msdata = ''
help_newexpname = ''
try:
    usage = "%(prog)s [-h] <msdata> <new_expname>"
    description="""Change the name of a project in a measurement set (MS).
    """
    import argparse
    parser = argparse.ArgumentParser(description=description, prog='expname.py', usage=usage)
    parser.add_argument('msdata', type=str, help=help_msdata)
    parser.add_argument('new_expname', type=str, help=help_newexpname)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    arguments = parser.parse_args()
    msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata
    new_expname = arguments.new_expname
except ImportError:
    usage = "%(prog)s [-h] <msdata> <new_expname>"
    description="""Change the name of a project in a measurement set (MS) to new_expname (in upper case).
    """
    # Compatibility with Python 2.7
    import optparse
    parser = optparse.OptionParser(usage=usage, description=description, prog='expname.py', version='%prog 1.0')
    theparser = parser.parse_args()
    arguments = theparser[1]
    #arguments = parser.parse_args()[1]
    if len(arguments) != 2:
        print('Two arguments must be provided: expname.py [-h] [-v] <msdata> <new_expname>')
        print('Use -h to get help.')
        sys.exit(1)

    msdata = arguments[0][:-1] if arguments[0][-1]=='/' else arguments[0]
    new_expname = arguments[1]

# The actual work
with pt.table(msdata+'/OBSERVATION', readonly=False, ack=False) as ms:
    old_project = ms.getcol('PROJECT')[0] # Should always be one-element list
    ms.putcol('PROJECT', [new_expname.upper()])

    # Sometimes it can happen that the OBSERVER is also the PROJECT, although not always
    if ms.getcol('OBSERVER')[0] == old_project:
        ms.putcol('OBSERVER', [new_expname()])

    ms.close()
    print('Experiment name changed to {}.'.format(new_expname.upper()))

