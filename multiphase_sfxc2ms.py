#!/usr/bin/python3
"""Takes the default {exp}_sfxc2ms.sh file produced by the
sfxc2ms.pl script and adds the _SRCname to the .cor files.

Generates different {exp}_sfxc2ms_SRCname.sh files for the
different phase centers (detailed in SRCname).


Benito Marcote
January 2018
JIVE
"""
import os
import sys
import stat
import glob
import argparse
#from astropy.io import ascii

# if len(sys.argv) != 3: #or sys.argv[1] == '-h':
#     print('multiphase_sfxc2ms.py <expname> <targetname>')
#     print('You need to specify the experiment name and the target source name')
#     print('as it is without the multi-phase center labeling')
#     print('(i.e. write only the text common to all the phase centers)')
#     sys.exit(1)

# expname = sys.argv[1].lower()
# target = sys.argv[2]


help_script = """Takes the default {exp}_sfxc2ms.sh file produced by the
sfxc2ms.pl script and adds the _SRCname to the .cor file names.

Generates different {exp}_sfxc2ms_{n-phasecenter}.sh files for the
different phase centers (detailed in SRCname).
"""
help_cals = """Should the calibrators be included in all measurement sets? (in the different phase centers)
By default they are include. If you set this option then they will be removed in all but the first pha. centers.
"""

parser = argparse.ArgumentParser(description=help_script)
parser.add_argument('-c', '--include-cals', default=True, dest='cals_on', action='store_false', help=help_cals)
parser.add_argument('expname', type=str, default=None, help='Experiment name')
parser.add_argument('target', type=str, default=None, help='Target name (without phase center suffixes)')

args = parser.parse_args()

expname = args.expname.lower()
target = args.target

#### NO NEED FOR THIS ANY MORE
# with open(expname+'.vxsm', 'r') as vexsumfile:
# The format is always (must be) ScanNo Time1 - Time2 0.0000 SRCname Stations
#vexsumfile = ascii.read(expname+'.vxsm')
#scans2src = {} # In the form {'No0001': 'SRCname'}
#for aline in vexsumfile:
#    scans2src[aline[0]] = aline[5]

# Gets all the names received by the target source for the different phase-centers
# Stranger: do not look at this line please
phc_names = list(set([i.split('_')[-1] for i in glob.glob('./*/*.cor_'+target+'*')]))
phc_suffixes = [i.replace(target, '') for i in phc_names]

with open(expname+'_sfxc2ms.sh', 'r') as shfile:
    # Create a file per phase center
    final_sh_files = [open(expname+'_sfxc2ms'+suff+'.sh', 'w') for suff in phc_suffixes]
    shlines = shfile.readlines()
    for ashline in shlines:
        if ashline[:4] == 'j2ms':
            tempfile = ashline.split(' ')
            corfile = tempfile[-1]
            corfile_existing = glob.glob(corfile[:-2]+'*')
	    #print(corfile)
	    #print(tempfile)
	    #print(corfile_existing)
            if len(corfile_existing) == 0:
		pass
	    
	    elif len(corfile_existing) == 1:
                for a_sh_file in final_sh_files:
                    a_sh_file.write(' '.join(tempfile[:-1])+' '+corfile_existing[0]+'\n')

            else:
                # This is the target, multiple phase centers.
                for i in range(len(phc_suffixes)):
                    final_sh_files[i].write(ashline[:-1]+'_'+target+phc_suffixes[i]+'\n')

        else:
            for a_sh_file in final_sh_files:
                a_sh_file.write(ashline)


for a_sh_file in final_sh_files:
    a_sh_file.close()

# Make the files executable
files = [expname+'_sfxc2ms'+suff+'.sh' for suff in phc_suffixes]
for a_file in files:
    #os.chmod(a_file, stat.S_IREAD | stat.S_IWUSR | stat.S_IEXEC)
    os.chmod(a_file, 0o755)


