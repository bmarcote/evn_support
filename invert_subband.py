#! /usr/bin/python3
"""
Invert the subband for specified antennas.

Usage: test_invert_subband.py msdata antennas [-sb SUBBANDS]
Options:
    msdata : str          MS data set containing the data to be swapged.
    antennas : str        Antenna or list of antennas that require to be
                          swapped. Use the two-letter name (e.g. Ef, Mc,
                          or Jb2). In case of more than one station, please
                          use either string 'Ef, Mc' or a non-spaced str:
                          Ef,Mc,Ys.

Version: 1.0
Date: Nov 2018
Written by Benito Marcote (marcote@jive.eu)
"""

import sys
import copy
import time
import argparse
from enum import IntEnum
import datetime as dt
import numpy as np
from pyrap import tables as pt


usage = "%(prog)s [-h] [-v] [-t1 STARTTIME] [-t2 ENDTIME]  <measurement set>  <antenna>"
description="""Invert the subband for specified antennas.

Fixes the problem when a subband is flipped (increasing frequency instead of decreasing along the
different channels. Observed it in Jb2 during 2018 Session 1 in spectral line observations.
"""
help_msdata = 'Measurement Set containing the data to be corrected.'
help_antenna = 'Name of the antenna to be corrected as it appears in the MS (case insensitive).'
help_t1 = 'Start time of the data that need to be corrected. By default the beginning of the observation.'\
          +'In Aips format: YYYY/MM/DD/hh:mm:ss or YYYY/DOY/hh:mm:ss'
help_t2 = 'Ending time of the data that need to be corrected. By default the ending of the observation.'\
          +'In Aips format: YYYY/MM/DD/hh:mm:ss or YYYY/DOY/hh:mm:ss'

parser = argparse.ArgumentParser(description=description, prog='polswap.py', usage=usage)
parser.add_argument('msdata', type=str, help=help_msdata)
parser.add_argument('antenna', type=str, help=help_antenna)
parser.add_argument('-t1', '--starttime', default=None, type=str, help=help_t1)
parser.add_argument('-t2', '--endtime', default=None, type=str, help=help_t2)
parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')

arguments = parser.parse_args()

msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata

def cli_progress_bar(current_val, end_val, bar_length=40):
        percent = current_val/end_val
        hashes = '#'*int(round(percent*bar_length))
        spaces = ' '*(bar_length-len(hashes))
        sys.stdout.write("\rProgress: [{0}] {1}%".format(hashes+spaces, int(round(percent*100))))
        sys.stdout.flush()


def chunkert(f, l, cs, verbose=True):
    while f<l:
        n = min(cs, l-f)
        yield (f, n)
        f = f + n


class Stokes(IntEnum):
    """The Stokes types defined as in the enum class from casacore code.
    """
    Undefined = 0 # Undefined value
    I = 1 # standard stokes parameters
    Q = 2
    U = 3
    V = 4
    RR = 5 # circular correlation products
    RL = 6
    LR = 7
    LL = 8
    XX = 9 # linear correlation products
    XY = 10
    YX = 11
    YY = 12
    RX = 13 # mixed correlation products
    RY = 14
    LX = 15
    LY = 16
    XR = 17
    XL = 18
    YR = 19
    YL = 20
    PP = 21 # general quasi-orthogonal correlation products
    PQ = 22
    QP = 23
    QQ = 24
    RCircular = 25 # single dish polarization types
    LCircular = 26
    Linear = 27
    Ptotal = 28 # Polarized intensity ((Q^2+U^2+V^2)^(1/2))
    Plinear = 29 #  Linearly Polarized intensity ((Q^2+U^2)^(1/2))
    PFtotal = 30 # Polarization Fraction (Ptotal/I)
    PFlinear = 31 # linear Polarization Fraction (Plinear/I)
    Pangle = 32 # linear polarization angle (0.5  arctan(U/Q)) (in radians)



def atime2datetime(atime):
    """Converts a string with the form YYYY/MM/DD/hh:mm:ss or YYYY/DOY/hh:mm:ss to MJD"""
    if atime.count('/') == 3:
        # Format: YYYY/MM/DD/hh:mm:ss
        return dt.datetime.strptime(atime, '%Y/%m/%d/%H:%M:%S')
    if atime.count('/') == 2:
        # Format: YYYY/DOY/hh:mm:ss
        return dt.datetime.strptime(atime, '%Y/%j/%H:%M:%S')
    else:
        raise ValueError('Date format must be YYYY/MM/DD/hh:mm:ss or YYYY/DOY/hh:mm:ss')



with pt.table(msdata, readonly=False, ack=False) as ms:
    # Get CORR_TYPE, the polarization entries in the data
    changes = None
    with pt.table(ms.getkeyword('ANTENNA'), readonly=True, ack=False) as ms_ant:
        antenna_number = [i.upper() for i in ms_ant.getcol('NAME')].index(arguments.antenna.upper())

    with pt.table(ms.getkeyword('OBSERVATION'), readonly=True, ack=False) as ms_obs:
        time_range = (dt.datetime(1858, 11, 17, 0, 0, 2) + \
                     ms_obs.getcol('TIME_RANGE')*dt.timedelta(seconds=1))[0]

    # Get the timerange to apply to polswap
    if arguments.starttime is not None:
        datetimes_start = atime2datetime(arguments.starttime)
    else:
        datetimes_start = time_range[0] - dt.timedelta(seconds=1)

    if arguments.endtime is not None:
        datetimes_end = atime2datetime(arguments.endtime)
    else:
        datetimes_end = time_range[1] + dt.timedelta(seconds=1)



    columns = ('DATA', 'FLOAT_DATA', 'FLAG', 'SIGMA_SPECTRUM', 'WEIGHT_SPECTRUM',
               'WEIGHT', 'SIGMA')
    # shapes of DATA, FLOAT_DATA, FLAG, SIGMA_SPECTRUM, WEIGHT_SPECTRUM: (nrow, npol, nfreq)
    # shapes of WEIGHT, SIGMA: (nrow, npol)
    columns = [a_col for a_col in columns if a_col in ms.colnames()]
    print('\nThe following columns will be modified: {}.\n'.format(', '.join(columns)))

    for (start, nrow) in chunkert(0, len(ms), 5000):
        cli_progress_bar(start, len(ms), bar_length=40)
        for changei, antpos in zip(changes, ('ANTENNA1','ANTENNA2')):
            ants = ms.getcol(antpos, startrow=start, nrow=nrow)
            datetimes = dt.datetime(1858, 11, 17, 0, 0, 2) + \
                        ms.getcol('TIME', startrow=start, nrow=nrow)*dt.timedelta(seconds=1)
            cond = np.where((ants == antenna_number) & (datetimes > datetimes_start) & (datetimes < datetimes_end))
            if len(cond[0]) > 0:
                for a_col in columns:
                    ms_col = ms.getcol(a_col, startrow=start, nrow=nrow)
                    if len(ms_col.shape) == 3:
                        ms_col[cond,] = ms_col[cond,][:,::-1,:]
                    elif len(ms_col.shape) == 2:
                        ms_col[cond,] = ms_col[cond,][:,::-1]
                    else:
                        raise ValueError('Unexpected dimensions for {} column.'.format(a_col))

                    ms.putcol(a_col, ms_col, startrow=start, nrow=nrow)


print('\n{} modified correctly.'.format(msdata))

