#!/usr/bin/env python3
"""Takes the default {exp}_sfxc2ms.sh file produced by the sfxc2ms.pl script and adds the _SRCname to the .cor files.

Generates different {exp}_sfxc2ms_SRCname.sh files for the different phase centers (detailed in SRCname).


Version: 2.0
Date: April 2018
Written by Benito Marcote (JIVE; marcote@jive.eu)


version 2.0 changes
- Major revision!
- Now you don't need to specify anymore the phase centers to consider
  (it had issues when the phase centers do not share a common label)
- It checks the {expname}.lis file to get the jobs that need to be considered.
- It gets the different phase-centers from the existing .cor files.
- Added an option to select a ref station (to include in the j2ms2 line).
- Added an option to exclude some of the phase centers that are in the data.

"""
import os
import sys
import glob
import argparse
#from astropy.io import ascii


help_script = """Create the *sfxc2ms.sh script that runs j2ms2 to create a MS file from all the *cor files.

Reads the {expname}.lis file to get a list of all the scans that must be included in the resulting MS.
For each scan checks if there is a {EXPNAME}_NoXXXX.cor* file under the current dir or subdirectory. In case this scan contains information for a multi phase-center, there should be more than one file with that name (called {EXPNAME}_NoXXXX.cor_targetname, where targetname will refer to the different given names for the different phase centers). It will append this cor file to the created *sh file in order to generate a different MS per phase center.

The different MS can optionally contain the information for the calibrators. This information can also go only to one of the phase centers, and the other ones could only contain the target information to save space (see options).

If no parameters are provided (apart of the mandatory, experiment name), then it will include all the sources and phase centers with cor files.
"""

help_cals = """Should the calibrators be included in all measurement sets? (in the different phase centers)
By default they are included. If you set this option then they will be removed in all but the first phase center.
"""

help_centers = """Phase-center source names. Provide a list (comma-separated, without spaces) of all the phase centers that have been produced and need to be included in the final dataset. NO NEEDED IF --BASE-NAME IS SET.
"""

help_exclude = """Phase-center source names to be excluded from the final dataset. Provide a list (comma-separated, without spaces) of those phase centers to be ignored (optional).
"""

# help_base_name = """Target name (without phase center suffixes).
# In case of the phase centers share a common prefix in the name of the source (e.g. the different phase centers are src1, src2, src3, ..., srcN), you can just provide the common part ('src' in the previous example) and the script will do the rest. NO NEEDED IF --PHASE-CENTERS IS SET.
# """

help_lisfile = """ (optional) '.lis' file to be loaded. This file is used to get a list of the scans that must be considered for the final MS files. By default it assumes that the file is located in the current directory with the name {expname}.lis. In any other case, this option must be set to localize such file.
"""

help_ref_station = """If you want to include the line eo_setup_ref_station:XX in the *sh file to run each j2ms2 line then you must specify here the station name (abreviation). 
"""

parser = argparse.ArgumentParser(description=help_script)
parser.add_argument('-i', '--include-cals', default=True, dest='cals_on', action='store_false', help=help_cals)
# parser.add_argument('-c', '--phase-centers', type=str, default=None, dest='centers', help=help_centers)
parser.add_argument('-e', '--exclude', type=str, default=None, dest='exclude', help=help_exclude)
parser.add_argument('-l', '--lis', type=str, default=None, dest='lisfile', help=help_lisfile)
# parser.add_argument('-t', '--base-name', type=str, default=None, dest='basename', help=help_base_name)
parser.add_argument('-r', '--ref-station', type=str, default=None, dest='ref_station', help=help_ref_station)
parser.add_argument('expname', type=str, default=None, help='Experiment name')

args = parser.parse_args()

expname = args.expname.lower()
lisfile = expname + '.lis'

if args.lisfile is not None:
    lisfile = args.lisfile


# List of all scans to include. Each of it is a string with the format No0000
scans_to_include = []
files_to_include = []
# Max number of SIMULTANEOUS phase centers. That is, in one single pointing.
max_number_of_phase_centers = -1

# Get the list of all the scans that must be considered. Those are selected by the + at the beginning
# of each line in the lis file.
with open(lisfile, 'r') as the_lisfile:
    lisfilelines = the_lisfile.readlines()
    for lisfileline in lisfilelines:
        # Some comments or other non-scan lines, only the ones starting with + are interesting
        if lisfileline[0] == '+':
            scans_to_include.append(lisfileline.split()[3])



def get_j2ms2_line(outputfile, corfile, ref_station=None):
    if ref_station is not None:
        return "j2ms2 eo:setup_ref_station={} -o {} {}\n".format(ref_station, outputfile, corfile)
    else:
        return "j2ms2 -o {} {}\n".format(outputfile, corfile)


if args.exclude is not None:
    args.exclude = args.exclude.split(',')

# Get all the cor files (including all phase-centers) ordered by scan
for a_scan in scans_to_include:
    scanfiles = glob.glob('./*/*{}.cor*'.format(a_scan))
    # Remove the phase centers to exclude
    if args.exclude is not None:
        for a_scanfile in scanfiles.copy():
            if a_scanfile.split('_')[-1] in args.exclude:
                scanfiles.remove(a_scanfile)

    files_to_include.append(scanfiles)
    if len(scanfiles) > max_number_of_phase_centers:
        max_number_of_phase_centers = len(scanfiles)
    
    if len(scanfiles) == 0:
        print('WARNING: Scan {} listed in the lis file has not been found.'.format(a_scan))



# Create all necessary lists of j2ms2 lines for each phase-center
class Group:
    """Simple class that defines a center name and a list of files.
    """
    def __init__(self):
        self._centername = ''
        self._centerlist = []
        self.files = []

    @property
    def center(self):
        return self._centername

    @center.setter
    def center(self, name):
        # Do not add the name is it is already in the self._centerlist
        if name not in self._centerlist:
            self._centerlist.append(name)
            self._centername = '_'.join(self._centerlist)


# Each group is defined as all the j2ms2 lines that will go to the same output (to the 'center'
# source), by reading all the cor files listed in 'files'
groups_j2ms2 = [Group() for i in range(max_number_of_phase_centers)]


for a_file in files_to_include:
    if len(a_file) == 1:
        # Include calibrators in all groups or only in the first one?
        if args.cals_on:
            for a_group in groups_j2ms2:
                a_group.files.append(a_file[0])
        else:
            groups_j2ms2[0].files.append(a_file[0])
    else:
        # a scan with phase-centers, can be eny length <= max_number_of_phase_centers
        for i, a_center in enumerate(sorted(a_file)):
            groups_j2ms2[i].files.append(a_center)
            groups_j2ms2[i].center = a_center.split('_')[-1]


# Prepare the final sh file!
with open(expname+'_sfxc2ms.sh', 'w') as shfile:
    shfile.write('#!/bin/bash\n')
    shfile.write('\\cp {}.vix {}.vix\n'.format(expname, expname.upper()))
    for a_group in groups_j2ms2:
        shfile.write('echo "Doing phase center {}"\n'.format(a_group.center))
        outfile = expname + '.ms_' + a_group.center
        for an_entry in a_group.files:
            shfile.write(get_j2ms2_line(outfile, an_entry, args.ref_station))


#os.chmod(a_file, stat.S_IREAD | stat.S_IWUSR | stat.S_IEXEC)
os.chmod(expname+'_sfxc2ms.sh', 0o755)

