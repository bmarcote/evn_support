#!/usr/bin/env python3
"""
Given a VEX file, it creates a new VEX file that is a subset of the given one,
dropping all the information (stations, source, PI names) that are not included
in the provided inputs.


Usage: split_vexfile.py [-o outputfile] <vexfile> <experiment> <PI name> <first scan> <last scan>

Options:
    vexfile : str       name of the original vex file (note that this file is not modified).

    experiment : str    name of the experiment for the final (output) vex file.
                        the original experiment name and all the other ones stored
                        in the vex file will be removed.

    pi name :str        name of the pi for this experiment. all the other names will
                        be removed.

    first scan : int    number of the first scan to be included in the new vex file.
                        all scans previous to this one will be removed from the vex file.

    last scan : int     number of the last scan to be included in the new vex file.
                        all scans after this one will be removed from the vex file.

optional parameters:
    -o outputfile : str  the filename for the output vex file. if not provided, the filename will
                         be <experiment>.vex


Version: 1.0
Date: May 2018
Written by Benito Marcote (marcote@jive.eu)
"""

import sys
import argparse
from vex import vex



usage = "%(prog)s [-h] [-v] [-o outputfile] <vexfile>  <experiment> <PI name> <scans>"
description="""Given a VEX file, it creates a new VEX file that is a subset of the given one,
dropping all the information (stations, source, PI names) that are not included in the provided inputs.

In e-EVN observations, where one VEX file contains different experiments, this script produces
a new VEX file containing the information for only one of the experiments. And thus the MS generated
by j2ms2 will not contain sensitive information from the other experiments.
"""

help_vexfile = 'Name of the original vex file to read (note that this file is not modified).'
help_experiment = """Name of the experiment for the final (output) vex file.
                     The original experiment name and all the other ones stored
                     in the vex file will be removed."""
help_piname = "Name of the PI for this experiment. all the other names will be removed."
help_firstscan ="""Number of the first scan to be included in the new vex file.
                   All scans previous to this one will be removed from the vex file."""
help_lastscan = """Number of the last scan to be included in the new vex file.
                   All scans after this one will be removed from the vex file."""

help_scans = """Scans to be included in the vex file. You can specify ranges or individual scans.
                Ranges can be specify as: XXX~YYY to include scans XXX to YYY, both included.
                Different individual scans or ranges can be provided as comma-separated lists
                (with no spaces in between). e.g.  100~110,150,120~130 to include scans
                100 to 110, 150, and 120 to 130."""

help_verbose = "Run in verbose mode. Prints all data to be discarded."
help_outputfile = "Filename for the output vex file. if not provided, the filename will be <experiment>.vex"


parser = argparse.ArgumentParser(description=description, prog='split_vexfile.py', usage=usage)

parser.add_argument('vexfile', type=str, help=help_vexfile)
parser.add_argument('experiment', type=str, help=help_experiment)
parser.add_argument('piname', type=str, help=help_piname)
# parser.add_argument('firstscan', type=int, help=help_firstscan)
# parser.add_argument('lastscan', type=int, help=help_lastscan)
parser.add_argument('scans', type=str, help=help_scans)
parser.add_argument('--version', action='version', version='%(prog)s 1.0')
parser.add_argument("-v", "--verbose", default=False, action="store_true" , help=help_verbose)
parser.add_argument("-o", "--outputfile", type=str, default=None, help=help_outputfile)

args = parser.parse_args()

verbose = args.verbose
if args.outputfile is None:
    outputfile = args.experiment.lower() + '.vex'
else:
    outputfile = args.outputfile

# assert args.firstscan <= args.lastscan


# Process the scans to be imported
scans_to_include = set()
scan_list = args.scans.split(',')
for a_scan_list in scan_list:
    if '~' in a_scan_list:
        # it is a range
        assert a_scan_list.count('~') == 1
        s1,s2 = [int(i) for i in a_scan_list.split('~')]
        assert s1 <= s2
        for i in range(s1, s2+1):
            scans_to_include.add(i)
    else:
        # it is an isolated scan
        scans_to_include.add(int(a_scan_list))



vexfile = vex.Vex(args.experiment, vexfile=args.vexfile)
if verbose:
    print(f'{args.vexfile} has been read')

# Updating experiment name
vexfile['GLOBAL']['EXPER'].value = args.experiment.upper()
if verbose:
    print(f'$GLOBAL>$EXPER updated to {args.experiment.upper()}')

oldexpname = [i for i in vexfile['EXPER'].keys() if 'comment' not in i]
if len(oldexpname) != 1:
    raise ValueError('Many definitions found under $EXPER. Only one expected.')

oldexpname = oldexpname[0]
vexfile['EXPER'][oldexpname].name = args.experiment.upper()
if verbose:
    print(f'$EXPER>def {oldexpname} updated to {args.experiment.upper()}')

vexfile['EXPER'][oldexpname]['exper_name'].value = args.experiment.upper()
if verbose:
    print(f'$EXPER>exper_name updated to {args.experiment.upper()}')


descr = vexfile['EXPER'][oldexpname]['exper_description'].value
if len(descr) > 1:
    if '"e-EVN' in descr[0]:
        descr[1] = f' {args.experiment.upper()}"'

vexfile['EXPER'][oldexpname]['exper_description'].value = descr
if verbose:
    print(f'$EXPER>exper_description updated to contain only {args.experiment.upper()}')

vexfile['EXPER'][oldexpname]['PI_name'].value = f'"{args.piname}"'
if verbose:
    print(f'EXPER>PI_name updated to {args.piname}')


# Keep sources that should be included
# Keep only specified scans
allsources = set([i for i in vexfile['SOURCE'].keys() if 'comment' not in i])
sources = set()
allscans = [i for i in vexfile['SCHED'].keys() if 'comment' not in i]

if len(scans_to_include) == 0:
    print('WARNING: no scans to be included')

for a_scan in allscans:
    scannumber = int(a_scan[2:])
    # if (scannumber < args.firstscan) or (scannumber > args.lastscan):
    if scannumber not in scans_to_include:
        del vexfile['SCHED'][a_scan]
        if verbose:
            print(f'Scan {a_scan} has been removed')

    else:
        # Double checking (in case the key exists, otherwise is within the 'start' key
        if 'source' in vexfile['SCHED'][a_scan]:
            sources.add(vexfile['SCHED'][a_scan]['source'].value)
        else:
            temp = vexfile['SCHED'][a_scan]['start'].value
            # print(temp)
            # print(temp.strip())
            # print(temp.strip().split(';'))
            temp = [vex.Entry.entry_from_text(i) for i in temp.strip().split(';')[1:]]
            sources.add([i.value for i in temp if i.key == 'source'][0])

# Remove the sources from other experiments
for a_source in allsources.difference(sources):
    del vexfile['SOURCE'][a_source]
    if verbose:
        print(f'Source {a_source} has been removed')


# Write the VEX info to a file
vexfile.to_file(outputfile)
if verbose:
    print(f'File {outputfile} has been written')




