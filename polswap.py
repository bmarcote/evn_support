#! /usr/bin/env python3
"""
Swap polarizations for specified antennas and for a specific timerange.

Usage: polswap.py msdata antennas [-sb SUBBANDS]
Options:
    msdata : str          MS data set containing the data to be swapged.
    antennas : str        Antenna or list of antennas that require to be
                          swapped. Use the two-letter name (e.g. Ef, Mc,
                          or Jb2). In case of more than one station, please
                          use either string 'Ef, Mc' or a non-spaced str:
                          Ef,Mc,Ys.

Version: 3.0
Date: March 2020
Written by Benito Marcote (marcote@jive.eu)

version 3.0 changes (March 2020)
- Columns with different dimensions grouped together in code.
- Fix memory bug.
- Not it modifies all expected columns for each chunk of (time) data.
  Before it was the opposite: modify one column at the time.
- Progress bar implemented.
version 2.0 changes (March 2020)
- MS read and modified in chunks of data.
- Simplified code.
- Bug Fix? Issues in a particular MS with the wrong station only available part of the time.
version 1.2 changes (July 2018)
- Several bug fixes.

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
description="""Swap polarizations for specified antennas.

Fixes the polarizations of an antenna that have been labeled incorrectly (R or X corresponds to L or Y,
respectively; and L or Y to R or X). It also changes accordingly the cross-pols per each baseline
containing the mentioned antenna (RL,LR, or XY,YX).

polswap.py works for both types of polarizations: circular and linear pols.
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
# parser.add_argument('--verbose', default=False, action='store_true')
# parser.add_argument('--timing', default=False, action='store_true')

arguments = parser.parse_args()

msdata = arguments.msdata[:-1] if arguments.msdata[-1]=='/' else arguments.msdata



def cli_progress_bar(current_val, end_val, bar_length=40):
        percent = current_val/end_val
        hashes = '#'*int(round(percent*bar_length))
        spaces = ' '*(bar_length-len(hashes))
        sys.stdout.write("\rProgress: [{0}] {1}%".format(hashes+spaces, int(round(percent*100))))
        sys.stdout.flush()


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



def chunkert(f, l, cs, verbose=True):
    while f<l:
        n = min(cs, l-f)
        yield (f, n)
        f = f + n


def atime2datetime(atime):
    """Converts a string with the form YYYY/MM/DD/hh:mm:ss or YYYY/DOY/hh:mm:ss to datetime"""
    if atime.count('/') == 3:
        # Format: YYYY/MM/DD/hh:mm:ss
        return dt.datetime.strptime(atime, '%Y/%m/%d/%H:%M:%S')
    if atime.count('/') == 2:
        # Format: YYYY/DOY/hh:mm:ss
        return dt.datetime.strptime(atime, '%Y/%j/%H:%M:%S')
    else:
        raise ValueError('Date format must be YYYY/MM/DD/hh:mm:ss or YYYY/DOY/hh:mm:ss')


def get_nedded_move(products, ant_order):
    """Returns the transposing necessary to do a polswap in one of the stations.
    Inputs
    ------
      products : 2-D array-like
            is the CORR_PRODUCT of the MS data. Sets the mapping of the stokes given
            two stations. e.g. [[0, 0], [1, 1], [0, 1], [1, 0]] represents that there
            are four stokes products, where the first two rows are the direct hands
            between antenna 1 (first column) and antenna 2 (second column).
      ant_order : int
            The position of the antenna in the CORR_PRODUCT (if the antenna to change
            is the ANT1 or ANT2, i.e. 0 or 1.

    Outputs
    -------
      changes : 1-D array-like
            The transposition of the columns necessary to make a swap pol for the antenna
            specified in ant_order.
            e.g. for the case mentioned before, if ANT1 is the one that needs to be converted,
            then the output 'changes' is [3, 2, 1, 0], as the stokes wanted at the end are:
            [[1, 0], [0, 1], [1, 1], [0, 0]]
    """
    pols_prod = list([list(j) for j in products])
    pols_prod_mod = np.copy(products)
    pols_prod_mod[:,ant_order] = products[:,ant_order] ^ 1
    pols_prod_mod = list([list(j) for j in pols_prod_mod])
    return np.array([pols_prod.index(i) for i in pols_prod_mod])


with pt.table(msdata, readonly=False, ack=False) as ms:
    # Get CORR_TYPE, the polarization entries in the data
    changes = None
    with pt.table(ms.getkeyword('ANTENNA'), readonly=True, ack=False) as ms_ant:
        antenna_number = [i.upper() for i in ms_ant.getcol('NAME')].index(arguments.antenna.upper())

    with pt.table(ms.getkeyword('POLARIZATION'), readonly=True, ack=False) as ms_pol:
        pols_order = [Stokes(i) for i in ms_pol.getcol('CORR_TYPE')[0]]
        # Check that the stokes are the correct ones to do a cross pol.
        # Only change it if circular or linear pols.
        for a_pol_order in pols_order:
            if (a_pol_order not in (Stokes.RR, Stokes.RL, Stokes.LR, Stokes.LL)) and \
               (a_pol_order not in (Stokes.XX, Stokes.XY, Stokes.YX, Stokes.YY)) and \
               (a_pol_order not in (Stokes.RX, Stokes.RY, Stokes.LX, Stokes.LY)) and \
               (a_pol_order not in (Stokes.XR, Stokes.XL, Stokes.YR, Stokes.YL)):

                print('Polswap only works for circular or linear pols (or both combined).')
                print('These data contain the following stokes: {}'.format(pols_order))
                ms.close()
                raise ValueError('Wrong stokes type.')

        # Get the column changes that are necessary
        pols_prod = ms_pol.getcol('CORR_PRODUCT')[0]
        # print(pols_prod)
        changes = [get_nedded_move(pols_prod, i) for i in (0, 1)]

    # transpose data for columns DATA, WEIGHT_SPECTRUM (if exists)
    # ants = [ms.getcol('ANTENNA1'), ms.getcol('ANTENNA2')]

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

    # shapes of DATA, FLOAT_DATA, FLAG, SIGMA_SPECTRUM, WEIGHT_SPECTRUM: (nrow, npol, nfreq)
    # shapes of WEIGHT, SIGMA: (nrow, npol)
    columns = ('DATA', 'FLOAT_DATA', 'FLAG', 'SIGMA_SPECTRUM', 'WEIGHT_SPECTRUM',
               'WEIGHT', 'SIGMA')
    # Only leave the ones that are in the MS. Not all of them are always present.
    columns = [a_col for a_col in columns if a_col in ms.colnames()]
    print('\nThe following columns will be modified: {}.\n'.format(', '.join(columns)))
    for (start, nrow) in chunkert(0, len(ms), 5000):
        cli_progress_bar(start, len(ms), bar_length=40)
        for changei, antpos in zip(changes, ('ANTENNA1','ANTENNA2')):
            ants = ms.getcol(antpos, startrow=start, nrow=nrow)
            datetimes = dt.datetime(1858, 11, 17, 0, 0, 2) + \
                        ms.getcol('TIME', startrow=start, nrow=nrow)*dt.timedelta(seconds=1)
            cond = np.where((ants == antenna_number) & (datetimes > datetimes_start) & (datetimes < datetimes_end))
            for a_col in columns:
                ms_col = ms.getcol(a_col, startrow=start, nrow=nrow)
                if len(ms_col.shape) == 3:
                    ms_col[cond,] = ms_col[cond,][:,:,:,changei,]
                elif len(ms_col.shape) == 2:
                    ms_col[cond,] = ms_col[cond,][:,:,changei,]
                elif len(ms_col.shape) == 1:
                    ms_col[cond,] = ms_col[cond,][:,changei,]
                else:
                    raise ValueError('Unexpected dimensions for {} column.'.format(a_col))

                ms.putcol(a_col, ms_col, startrow=start, nrow=nrow)


print('\n{} modified correctly.'.format(msdata))

