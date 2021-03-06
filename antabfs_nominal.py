#!/usr/bin/env python3
"""
Python port of Bob Campbell's IDL script to make nominal tsys tables.
It takes the nominal SEFD values from the sefd_values.txt table and generates an ANTAB file using
these values. Gains will be set to 1/SEFD, and all Tsys to 1.0.
Note that it will overwrite any existing ANTAB file in the current path.
 
Version: 4.3
Date: Sep 2018
Author: Benito Marcote (marcote@jive.eu) & Jay Blanchard (blanchard@jive.eu)

version 4.3 changes
- Fixed issue when giving SEFD, not ignores that antenna may not be in status table
version 4.2 changes
- Explicit error if antenna or freq. is not known
version 4.1 changes
- Minor issues (ordering input arguments, version)
version 4.0 changes
- Major code changes for a better exception handling 
version 3.0 changes
- new argument to set the freq. interval (-fr / --freqrange)
version 2.0 changes
- interactive or argument-based
- documentation!!
- Takes SEFD values from status table of EVN
"""
import os
import sys
import argparse
import datetime as dt
from math import floor
from collections import defaultdict


__version__ = 4.2
help_str = """Writes a nominal SEFD ANTAB file. Gain will be set to 1/SEFD, and all Tsys to 1.0.
It will overwrite any previous antab file in the current path.
antabfs_nominal.py uses the SEFD information from sefd_values.txt to compute the nominal values.
Creates (or overwrites) a file called <experiment><antenna>.antabfs, where <experiment> and
<antenna> are the input from the user.
"""
parser = argparse.ArgumentParser(description=help_str, prog='antabfs_nominal.py')
parser.add_argument('antenna', type=str, default=None, help='Antenna name (two-letters syntax, except for Jb1 Jb2 Ro7 Ro3)')
parser.add_argument('experiment', type=str, default=None, help='Experiment name')
parser.add_argument('start', type=str, default=None, help='Start time (DOY/HH:MM, YYYY/DOY/HH:MM or YYYY/MM/DD/HH:MM)')
parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))
parser.add_argument('-b', '--band', type=str, default=None, help='Observed band (in cm). REQUIRED unless SEFD provided')
parser.add_argument('-d', '--duration', type=float, default=24, help='Duration of the experiment (in hours). Default: 24 h')
parser.add_argument('-fr', '--freqrange', type=str, default='100,100000', help='Frequency range where the ANTAB is applicable (lower and upper limit, in MHz). Default 100,100000 (please, do not use spaces between the numbers).')
parser.add_argument('-s', '--sefd', type=float, default=None, help='SEFD to be used (optional). Default values are loaded.')
parser.add_argument('-i', '--interval', type=float, default=0.25, help='Interval between Tsys measurements (in min). Default: 0.5')
parser.add_argument('-sb', '--subbands', type=int, default=8, help='Number of subbands in the experiment. Default: 8 = L1|R1 L2|R2 ... L8|R8')

args = parser.parse_args()

i_already_warn_about_seconds = False


def read_sefd_table(tablename=os.path.dirname(__file__)+'/sefd_values.txt'):
    sefd_table = open(tablename, 'r')
    titles = sefd_table.readline().strip().split('|')
    titles = [t.strip() for t in titles]
    sefd_dict = defaultdict(dict)
    for an_ant in sefd_table.readlines():
        values = [t.strip() for t in an_ant.strip().split('|')]
        for i in range(1, len(values)):
            if values[i] != '':
                sefd_dict[values[0].lower()][titles[i]] = float(values[i])
    return sefd_dict



def read_sefd_values(table, antenna, band):
    if args.sefd is not None:
        # Then no need of getting the information from the table
        return args.sefd

    if antenna not in table:
        print('ERROR: {} is not available.\n'.format(antenna))
        print('The available antennas are: {}'.format(' '.join(table.keys())))
        sys.exit(1)
    elif band not in table[antenna]:
        print('ERROR: antenna {} does not have SEFD information for {}-cm observations'.format(antenna, band))
        print('{} only has SEFD information for {} cm'.format(antenna, ', '.join(table[antenna].keys())))
        sys.exit(1)
    else:
        return table[antenna][band]


def index_header():
    indexes = list()
    for i in range(1, args.subbands+1):
        indexes.append("'R{n}|L{n}'".format(n=i))
    return ','.join(indexes)


def get_header(antenna, gain, freqrange):
    """Returns the apropiate header for the given antenna using a given gain value.
    
    Inputs:
      antenna : str
        The antenna name (two letters syntax)
      gain : float
        The gain (in 1/Jy) for this antenna
    """
    generic_header = '''!
! Nominal calibration data for {ant} created by
! antabfs_nominal.py (version {version})
! Script at JIVE done by Benito Marcote & Jay Blanchard
!
GAIN {ant} ELEV DPFU={gain},{gain} POLY=1.0 FREQ={freqrange}
/
TSYS {ant} FT=1.0 TIMEOFF=0
INDEX = {indexes}
/'''
    return generic_header.format(ant=antenna[:2].upper(), gain=gain, indexes=index_header(),
                       version=__version__, freqrange=','.join([str(i) for i in freqrange]))


def hm2hhmmss(hhmm):
    """Takes a time in str format HH:MM.MM and returns int(hh), int(mm), float(ss)"""
    try:
        hour, minute = hhmm.split(':')
    except ValueError:
        if not i_already_warn_about_seconds:
            print('WARNING: only HH:MM are read. Seconds or other smaller numbers are going to be ignored.')
            i_already_warn_about_seconds = True

        hour, minute, *others = hhmm.split(':')

    minute = float(minute)
    second = int((minute-floor(minute))*60)
    return int(hour), int(floor(minute)), second


def date2datetime(date):
    """Convert the given date to DOY, HH, MM.
    Inputs:
      date : str
        Date in format DOY/HH:MM, YYYY/DOY/HH:MM or YYYY/MM/DD:HH:MM
    """
    if date.count('/') == 1:
        # Uses a fake year
        doy, hhmm = date.split('/')
        return dt.datetime(1969, 1, 1, *hm2hhmmss(hhmm)) + dt.timedelta(int(doy)-1)
    elif date.count('/') == 2:
        year, doy, hhmm = date.split('/')
        return dt.datetime(int(year), 1, 1, *hm2hhmmss(hhmm)) + dt.timedelta(int(doy)-1)
    elif date.count('/') == 3:
        year, month, day, hhmm = date.split('/')
        return dt.datetime(int(year), int(month), int(day), *hm2hhmmss(hhmm))
    else:
        print('ERROR: date must have the following format: DOY/HH:MM, YYYY/DOY/HH:MM or YYYY/MM/DD:HH:MM')
        raise SyntaxError



def date2string(datetime):
    """Return a string with the date in the correct ANTAB format
    """
    return '{} {:02d}:{:05.2f}'.format(datetime.strftime('%j'), datetime.hour, datetime.minute+datetime.second/60.)



#currently asks for inputs, might change this in future to read from vex...
if args.experiment == None:
    args.experiment = raw_input("Input experiment name: ")

if args.antenna == None:
    args.antenna = raw_input("Input antenna name (two-letter syntax (except Jb1 Jb2 Ro7 Ro3): ")

if args.band == None and args.sefd == None:
    output = raw_input("Input frequency band (cm) or SEFD value (Jy). Write 'band VALUE' or 'sefd VALUE'").split(' ')
    if output[0].lower() == 'band':
        args.band = output[1]
    elif output[0].lower() == 'sefd':
        args.sefd = output[1]
    else:
        print('Wrong format. It must be either: "band VALUE" or "sefd VALUE"')
        raise ValueError


if args.start == None:
    input_starttime = raw_input("Enter start day of the year, hour and minute (comma separated):  ").split(',')
    args.start = '{} {}:{}'.format(*input_starttime)
    dur = raw_input("Enter duration (hours; enter to default): ")
    if dur != '':
        args.duration = float(dur)


# Read and interpretate the freqrange.

if args.freqrange.count(',') != 1:
    print('The frequency range (--freqrange) must contain two values (comma-separated): the lower and upper frequency limit in MHz (please, do not use spaces between the numbers).')
    sys.exit(1)

args.freqrange = [int(i) for i in args.freqrange.split(',')]

if not (args.freqrange[0] < 30*1000/float(args.band) < args.freqrange[1]):
    print('The provided frequency range must contain the frequency band, and this is not the case.')
    print('Introduced band: {} GHz'.format(30/float(args.band)))
    print('Introduced frequency range: {}-{} GHz'.format(args.freqrange[0]/1e3, args.freqrange[1]/1e3))
    sys.exit(1)


sefd_info = read_sefd_table()

start_time = date2datetime(args.start)
end_time = start_time + dt.timedelta(args.duration/24.)
a_time = date2datetime(args.start)

# Creating the ANTAB file
antab_file = open('{}{}.antabfs'.format(args.experiment.lower(), args.antenna.lower()[:2]), 'wt')
antab_file.write(get_header(args.antenna.lower(), 1./read_sefd_values(sefd_info, args.antenna.lower(), args.band),
                            args.freqrange)+'\n')

while a_time < end_time:
   antab_file.write('{}{}\n'.format(date2string(a_time), ' 1.0'*args.subbands))
   a_time = a_time + dt.timedelta(args.interval/(60*24.))

antab_file.write('/\n') # antab expects trailing /
antab_file.close()

print('File {}{}.antabfs created successfully.'.format(args.experiment.lower(), args.antenna.lower()[:2]))

