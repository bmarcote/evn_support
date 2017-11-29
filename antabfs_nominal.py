#!/usr/bin/python3

# python port of Bob Campbells IDL script to make fake tsys tables...
# python 2 at the moment for raw_input
# Jay Blanchard 2016
# Benito 2016
# Improved version with:
# - interactive or argument-based
# - documentation!!
# - Takes SEFD values from status table of EVN

import argparse
import datetime as dt
from math import floor
from collections import defaultdict

#Usage: SEFD.pl <SEFD> <DOY> <experiment name> <telescope>


help_str = """This script will write a nominal SEFD ANTAB format file.
    Gain will be set to 1/SEFD, and all Tsys to 1.0.
    It will overwrite any previous antab file in the current path.
    """
parser = argparse.ArgumentParser(description='help_str')
parser.add_argument('antenna', type=str, default=None, help='Antenna name (two-letters syntax, except for Jb1 Jb2 Ro7 Ro3)')
parser.add_argument('experiment', type=str, default=None, help='Experiment name')
parser.add_argument('start', type=str, default=None, help='Start time (DOY/HH:MM, YYYY/DOY/HH:MM or YYYY/MM/DD/HH:MM)')
parser.add_argument('-d', '--duration', type=float, default=24, help='Duration of the experiment (in hours). Default: 24 h')
parser.add_argument('-b', '--band', type=str, default=None, help='Observed band (in cm). Optional only if SEFD provided')
parser.add_argument('-s', '--sefd', type=float, default=None, help='SEFD to be used (optional). Default values are loaded.')
parser.add_argument('-i', '--interval', type=float, default=0.25, help='Interval between Tsys measurements (in min). Default: 0.5')
parser.add_argument('-sb', '--subbands', type=int, default=8, help='Number of subbands in the experiment. Default: 8 = L1|R1 L2|R2 ... L8|R8')

args = parser.parse_args()

i_already_warn_about_seconds = False

def read_sefd_table(tablename='/jop83_0/pipe/in/marcote/scripts/sefd_values.txt'):
    sefd_table = open(tablename, 'r')
    titles = sefd_table.readline().strip().split('|')
    titles = [t.strip() for t in titles]
    sefd_dict = defaultdict(dict)
    for an_ant in sefd_table.readlines():
        values = [ t.strip() for t in an_ant.strip().split('|')]
        for i in range(1, len(values)):
            if values[i] != '':
                sefd_dict[values[0].lower()][titles[i]] = float(values[i])
    return sefd_dict



def read_sefd_values(table, antenna, band):
    try:
        return table[antenna][band]
    except KeyError:
        print('Error: either the antenna does not exist or it does not have information at that band.')
        print('Available antennas with code:')
        print(' '.join(table.keys()))
        raise KeyError


def index_header():
    indexes = list()
    for i in range(1, args.subbands+1):
        indexes.append("'R{n}|L{n}'".format(n=i))
    return ','.join(indexes)


def get_header(antenna, gain):
    """Returns the apropiate header for the given antenna using a given gain value.
    
    Inputs:
      antenna : str
        The antenna name (two letters syntax)
      gain : float
        The gain (in 1/Jy) for this antenna
    """
    generic_header = '''!
! Nominal calibration data for {ant} by tsys_nominal.py.
! tsys_nominal.py version 2.0, 2016 August 3, BM & JB
!
GAIN {ant} ELEV DPFU={gain},{gain} POLY=1.0 FREQ=100,100000
/
TSYS {ant} FT=1.0 TIMEOFF=0
INDEX = {indexes}
/'''
    return generic_header.format(ant=antenna[:2].upper(), gain=gain, indexes=index_header())


def hm2hhmmss(hhmm):
    """Takes a time in str format HH:MM.MM and returns int(hh), int(mm), float(ss)"""
    try:
        hour, minute = hhmm.split(':')
    except ValueError:
        if not i_already_warn_about_seconds:
            print('WARNING: only HH:MM are read. Seconds or other smaller numbers are going to be ignored.')
            i_already_warn_about_seconds  = True

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
        print('Error: date must have the following format: DOY/HH:MM, YYYY/DOY/HH:MM or YYYY/MM/DD:HH:MM')
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


sefd_info = read_sefd_table()


start_time = date2datetime(args.start)
end_time = start_time + dt.timedelta(args.duration/24.)
a_time = date2datetime(args.start)

# Creating the ANTAB file
antab_file = open('{}{}.antabfs'.format(args.experiment.lower(), args.antenna.lower()[:2]), 'wt')
antab_file.write(get_header(args.antenna.lower(), 1./read_sefd_values(sefd_info, args.antenna.lower(), args.band))+'\n')

while a_time < end_time:
   antab_file.write('{}{}\n'.format(date2string(a_time), ' 1.0'*args.subbands))
   a_time = a_time + dt.timedelta(args.interval/(60*24.))

antab_file.write('/\n') # antab expects trailing /
antab_file.close()

print('File {}{}.antabfs created successfully.'.format(args.experiment.lower(), args.antenna.lower()[:2]))
