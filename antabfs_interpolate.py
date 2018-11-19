#!/usr/bin/env python3
description = """
Given an ANTAB file, it creates a new one with more Tsys values that are interpolated from the
given ones. This will fill gaps when the time separation between Tsys measurements is too long
(and e.g. AIPS starts flagging scans because there is not Tsys information for them).

IMPORTANT CONSIDERATIONS:
Note that it interpolates data with a smooth function, avoiding outliers or zero values.
However, it does not consider scan boundaries, so if Tsys are recorded in different sources
it can introduce biases. Therefore, it assumes that the Tsys should not change quickly
(e.g. no change of sources).

Version: 2.0
Date: Aug 2018
Written by Benito Marcote (marcote@jive.eu)


version 2.0 changes
- (MAJOR) Now it does an actual interpolation of the data (linear spline with smoothing).
- Keeps comment lines in the output file (except the ones within the data).
- Allows you to specify a custom time range for the final antab file.

"""

# import pdb
import sys
import os
import argparse
import datetime as dt
import numpy as np
from scipy import interpolate



usage = "%(prog)s [-h] [-v] [-p] [-o OUTPUTFILE] [-tini STARTIME] [-tend ENDTIME] antabfile int"
help_tini = 'Starttime of the Tsys measurements. In case you want to modify it from the original file. It will extrapolate the earliest Tsys original values. The format must be as DOY/HH:MM:SS.'
help_tend = 'Ending time of the Tsys measurements. In case you want to modify it from the original file. It will extrapolate the latest Tsys original values. The format must be as DOY/HH:MM:SS.'
help_plot = 'Produce plots (per column) with the original values and the interpolation.'

parser = argparse.ArgumentParser(description=description, prog='antabfs_interpolate.py', usage=usage,
                                formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('antabfile', type=str, help='The antabfs file to be read.')
parser.add_argument('int', type=float, help='The interval (in seconds) between the final Tsys measurements')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 2.0')
parser.add_argument('-o', '--output', type=str, default=None, help='Output filename. By default same as antabfile.')
parser.add_argument('-p', '--plot', default=False, action='store_true', help=help_plot)
parser.add_argument('-tini', type=str, default=None, help=help_tini)
parser.add_argument('-tend', type=str, default=None, help=help_tend)

args = parser.parse_args()




antab = open(args.antabfile, 'r+').readlines()

# Reads the current antab file and loads the Tsys values and all the data
antab_times = []
antab_data = []
indexes = []
for aline in antab:
    if aline[0].lstrip().isdigit():
        # Then this line is a Tsys input
        temp = aline.split()
        # First column is DOY, second one is HH:MM.MM or HH:MM:SS
        if temp[1].count(':') == 1:
            temp2 = temp[1].split('.')
            temp2[1] = '{:02.0f}'.format(60*float('0.'+temp2[1]))
            temp[1] = ':'.join(temp2)
        elif temp[1].count(':') == 2:
            # Nothing to do
            if temp[1].count('.') != 0:
                temp[1] = temp[1].split('.')[0]
            pass
        else:
            raise ValueError('Time format not supported: {}'.format(temp[1]))

        antab_times.append(dt.datetime.strptime(' '.join(temp[0:2]), '%j %H:%M:%S').timestamp())
        antab_data.append([float(i) for i in temp[2:]])
    else:
        if 'INDEX' in aline:
            indexes = [i.replace("'", '').strip() for i in aline.split('=')[1].replace('/', '').replace('\n', '').split(',')]


antab_data = np.array(antab_data)

n_columns = antab_data.shape[1]

assert n_columns == len(indexes)

# For each column, do a spline fit, with the data weighted proportionally to the square of
# their deviation from the median value.

fits = [None]*n_columns
for i in np.arange(n_columns):
    weights = np.abs((antab_data[:,i] - np.median(antab_data[:,i]))/np.median(antab_data[:,i]))
    # For zero values, consider a value of 1e-3, which would imply an uncertainty in the weight of 0.1%
    # This is done to avoid division by zero in the interpolation
    weights[np.where(weights == 0.0)] = 1e-3
    # s = 1e4 looks optimal to remove large outliers in the ANTAB information
    # to be less drastic, you could use 1e3.
    # Lower values will produce peaks to outliers
    fits[i] = interpolate.splrep(antab_times, antab_data[:,i], w=1/weights**2, k=1, s=1e4)




tsys_timestamps = None
tsys = None

with open(args.antabfile+'.tmp', 'wt') as newfile:
    # Write all the header
    for aline in antab:
        if not aline[0].isdigit():
            newfile.write(aline)
        else:
            break

    if args.tini is None:
        tsys_times_ini = dt.datetime.fromtimestamp(antab_times[0])
    else:
        tsys_times_ini = dt.datetime.strptime(args.tini, '%j/%H:%M:%S')

    if args.tend is None:
        tsys_times_end = dt.datetime.fromtimestamp(antab_times[-1])
    else:
        tsys_times_end = dt.datetime.strptime(args.tend, '%j/%H:%M:%S')

    tsys_times = np.arange(tsys_times_ini, tsys_times_end, dt.timedelta(seconds=args.int))
    tsys_timestamps = np.array([i.tolist().timestamp() for i in tsys_times])
    plot_times = tsys_timestamps
    tsys = np.empty((len(tsys_times), n_columns))
    for acol in range(n_columns):
        tsys[:,acol] = interpolate.splev(tsys_timestamps, fits[acol], der=0)

    for a_time,a_entry in zip(tsys_timestamps, tsys):
        temp = ['{:6.1f}'.format(i) for i in a_entry]
        newfile.write('{} {}\n'.format(dt.datetime.fromtimestamp(a_time).strftime('%j %H:%M:%S'), ' '.join(temp)))

    newfile.write('/\n')


if args.output is None:
    os.rename(args.antabfile+'.tmp', args.antabfile)
    print('The antab file {} has been updated.'.format(args.antabfile))
else:
    os.rename(args.antabfile+'.tmp', args.output)
    print('The antab file {} has been created.'.format(args.output))


# Testing purposes: plot the original data and the final one
if args.plot:
    import matplotlib.pyplot as plt
    for i in range(n_columns):
        plt.figure()
        plt.plot(antab_times, antab_data[:,i], 'oC0')
        plt.plot(tsys_timestamps, tsys[:,i], '-C1')
        plt.xlabel(r'Timestamp')
        plt.ylabel(r'Tsys')
        plt.title('Column: {}'.format(indexes[i]))

    plt.show()
