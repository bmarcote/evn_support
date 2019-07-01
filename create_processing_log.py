#!/usr/bin/python3.6

description = """Script to create a processing.log file to be used during the post-processing
of an EVN experiment following the standard EVN post-processing steps.

This saves time as it does not require to copy the file from a previous experiment.
Only a really few changes will be necessary in the file during the procedure (apart
of writting down the appropiate comments).


Author: Bentio Marcote (marcote@jive.eu)
Version: 1.7
Date: Jul 2019

version 1.7
- Minor upgrades on written text.
version 1.6
- Bug fix wrong expcode to get the obs date in e-EVN exps.
version 1.5
- Bug fix getting the data when expname was lower cases.
version 1.4
- ccsbeta references changed to ccs (change of computer).
version 1.3
- Added the comment_tasav_file.py and PI letter customization steps.
version 1.2
- date is now optional. If not specified, then it takes it from MASTER_PROJECTS.LIS in ~jops

"""

import os
import sys
import argparse
import subprocess
from datetime import datetime as dt


# Options for the argparse
usage = '%(prog)s [-h] [-d OBSDATE] [-e eEVN_session] [-jss SupSci] [-o outputfile] <experiment name>'
help_eEVN = 'If this is an e-EVN experiment with a name different to the one used for the vex file, '\
            +'then provide the exp. name used to set the vex file.'

parser = argparse.ArgumentParser(description=description, prog='create_processing_log.py', usage=usage)
parser.add_argument('expname', type=str, help='Name of the experiment to process')
parser.add_argument('-d', '--date', type=str, default=None, help='Date of the observations (in YYMMDD format)')
parser.add_argument('-e', '--eEVN', type=str, default=None, help=help_eEVN)
parser.add_argument('-jss', type=str, default='marcote', help='Name of the Support Scientist running this')
parser.add_argument('-o', type=str, default='processing.log', help='Output file (default: processing.log)')

args = parser.parse_args()


ofile = open(args.o, mode='w')

# The experiment name stored in the vexfile/ccs for these data (same as expname for
# normal experiments, but args.eEVN in the case of e-EVN experiments).
if args.eEVN is None:
    masterexp = args.expname
else:
    masterexp = args.eEVN


if args.date is not None:
    obsdate = dt.strptime(args.date, '%y%m%d')
else:
    # Depends on the experiment only one of these work properly
    date = subprocess.getoutput('ssh jops@ccs grep {} /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 3'.format(masterexp.upper()))
    if date == '':
        date = subprocess.getoutput('ssh jops@ccs grep {} /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 4'.format(masterexp.upper()))
    obsdate = dt.strptime(date.strip(), '%Y%m%d')


# Header of the file
ofile.write(f"""{'#'*20}
# {args.expname.upper()}
# {'EVN' if args.eEVN is None else 'e-EVN'} experiment at ? band
# Observed on {obsdate.strftime('%d %B %Y')}
#
# File created on {dt.today().strftime('%A %d %B %Y')}
# by {args.jss.title()}
#
{'#'*20}\n
""")


# ccs steps
if args.eEVN is None:
    ofile.write('# In ccs:\n')
    ofile.write('ssh -Y jops@ccs\n')
    ofile.write(f'cd /ccs/expr/{masterexp.upper()}\n\n')
    ofile.write('# Create the lis file (two possible methods):\n')
    ofile.write(f'showlog_new {masterexp.upper()}  # (graphically)\n')
    ofile.write(f'make_lis -e {masterexp.lower()} -p prod -s {masterexp.lower()}.lis # (without graphical window)\n')
    ofile.write(f'checklis {masterexp.lower()}.lis\n\n')
else:
    ofile.write('# In ccs:\n')
    ofile.write('# -- All the necessary steps should already have been conducted for the main experiment (the one used to assign the name of the vex file). No further steps here are required\n\n\n')

# Back to ee
ofile.write('# Back to ee\n')
ofile.write(f'scp jops@ccs:/ccs/expr/{masterexp.upper()}/{masterexp.lower()}.vix ./{args.expname.lower()}.vix\n')
ofile.write(f'scp jops@ccs:/ccs/expr/{masterexp.upper()}/{masterexp.lower()}.lis ./{args.expname.lower()}.lis\n\n')

ofile.write(f'scp jops@jop83:piletters/{args.expname.lower()}.piletter .\n')
ofile.write(f'scp jops@jop83:piletters/{args.expname.lower()}.expsum .\n\n')

ofile.write(f'ln -s {args.expname.lower()}.vix {args.expname.upper()}.vix\n\n')
ofile.write('# Modify the lis file (header and jops to be included)\n\n')
ofile.write(f'getdata.pl -proj {masterexp.upper()} -lis {args.expname.lower()}.lis\n\n')
ofile.write(f'j2ms2 -v {args.expname.lower()}.lis\n')
ofile.write(f'# If devel version is required:\n')
ofile.write(f'/home/verkout/src/jive-casa/build2/apps/j2ms2/j2ms2 -v {args.expname.lower()}.lis\n\n')

ofile.write('# Using jplotter to do standard plots\n\n')
ofile.write('# If already available:\n')
ofile.write(f'standardplots -weight {args.expname.lower()}.ms <REFANT> <CALSRC>\n\n\n\n')
ofile.write('# Otherwise:\n')
ofile.write('jplotter\n\n')
ofile.write(f'ms {args.expname.lower()}.ms\n')
ofile.write('indexr\n')
ofile.write('r\n\n\n\n')
ofile.write('# weights plot\n')
ofile.write('bl auto;fq 0:7/p;sort bl sb;pt wt;ckey sb;ptsz 4;pl\n')
ofile.write(f'save {args.expname.lower()}-weight.ps\n\n')
ofile.write('# ampphase plot\n')
ofile.write('bl Ef* -auto;fq 5/p;ch 0.1*last:0.9*last;avc vector;nxy 1 4;pt anptime;ckey src;y local;ptsz 2;time none;pl\n')
ofile.write(f'save {args.expname.lower()}-ampphase-1.ps\n\n')
ofile.write('time 2017/11/04/10:00:00 to +50m;pl\n')
ofile.write(f'save {args.expname.lower()}-ampphase-2.ps\n\n')
ofile.write('# auto-corr plots\n')
ofile.write('listr\n')
ofile.write('scan 1;bl auto;fq */p;ch none;avt vector;avc none;pt ampchan;ckey p;sort bl;new sb false;multi true;y 0 1.6;nxy 1 4;pl\n')
ofile.write(f'save {args.expname.lower()}-auto-1.ps\n\n')
ofile.write('scan 91;pl\n')
ofile.write(f'save {args.expname.lower()}-auto-2.ps\n\n')
ofile.write('# cross-corr plots\n')
ofile.write("scan 1;pt anpchan;bl Ef* -auto;fq *;ckey p['RR']=2 p['LL']=3 p['RL']=4 p['LR']=5;nxy 2 3;y local;draw lines points;multi true;new sb false;ptsz 4;sort bl sb;pl\n")
ofile.write(f'save {args.expname.lower()}-cross-1.ps\n\n')
ofile.write('scan 91;pl\n')
ofile.write(f'save {args.expname.lower()}-cross-2.ps\n\n')
ofile.write('exit\n\n\n')


ofile.write('# If Yebes (or Hobart) is in the array\n')
ofile.write(f'ysfocus.py {args.expname.lower()}.ms\n\n')

ofile.write(f'flag_weights.py {args.expname.lower()}.ms 0.9\n\n\n\n')

ofile.write(f'tConvert {args.expname.lower()}.ms {args.expname.lower()}_1_1.IDI\n\n')

ofile.write('# Password for the experiment (generated with date | md5sum | cut -b 1-12):\n')
passwd = str(os.popen('date | md5sum | cut -b 1-12').read())[:-1]
ofile.write(f'touch {args.expname.lower()}_{passwd}.auth\n\n')
ofile.write('# Edit the piletter\n\n')
ofile.write('gzip *ps\n')
ofile.write('archive -auth -e {0}_{1} -n {0} -p {2}\n'.format(args.expname.lower(), obsdate.strftime('%y%m%d'), passwd))
ofile.write('archive -stnd -e {0}_{1} {0}.piletter *ps.gz\n'.format(args.expname.lower(), obsdate.strftime('%y%m%d')))
ofile.write('archive -fits -e {0}_{1}  *IDI*\n\n'.format(args.expname.lower(), obsdate.strftime('%y%m%d')))
ofile.write('# In case it is necessary (if the proposal was not sent through NorthStar):\n')
ofile.write('archive -abstract <abstract.txt> -e {0}_{1}\n\n'.format(args.expname.lower(), obsdate.strftime('%y%m%d')))

ofile.write('# Let\'s pipeline\n\n')
ofile.write('ssh -Y pipe@jop83\n\n')
ofile.write(f'mkdir $IN/{args.expname.lower()}\n')
ofile.write(f'mkdir $OUT/{args.expname.lower()}\n')
ofile.write(f'mkdir $IN/{args.jss.lower()}/{args.expname.lower()}\n')
ofile.write('cd !$\n\n')

ofile.write('# Get all log, antab, uvflg tables from vlbeer\n')
ofile.write('sftp evn@vlbeer.ira.inaf.it\n\n')
ofile.write(f"cd vlbi_arch/{obsdate.strftime('%b%y').lower()}\n\n")
ofile.write('mget {0}*.log {0}*.antabfs {0}*.uvflgfs\n\n'.format(args.expname.lower()))

ofile.write("# If necessary, create the antab file with antabfs.pl, antabfs.py, or tsys.py\n")
ofile.write("# If necessary, interpolate antab files with antabfs_interpolate.py <antab>\n")
ofile.write("# If necessary, create nominal antab files with antabfs_nominal.py ...\n\n")
ofile.write("uvflgall.csh\n\n")
ofile.write("# Combine all uvflgfs and antabfs files:\n")
ofile.write("cat {0}*.antabfs > {0}.antab\n".format(args.expname.lower()))
ofile.write("cat {0}*.uvflgfs > {0}.uvflg\n\n".format(args.expname.lower()))
ofile.write("cp {0}.* $IN/{0}/\n\n".format(args.expname.lower()))

ofile.write("# Prepare the inputs for the pipeline (copy inp and tasav.txt from a previous experiment)\n")
ofile.write(f"vim {args.expname.lower()}.tasav.txt\n")
ofile.write(f"vim {args.expname.lower()}.inp.txt\n\n")
ofile.write(f"EVN.py {args.expname.lower()}.inp.txt\n\n")

ofile.write(f'cd $OUT/{args.expname.lower()}\n\n')
ofile.write("# Create the .comment and .tasav files\n")
ofile.write(f"comment_tasav_file.py {args.expname.lower()}\n")
ofile.write(f'vim {args.expname.lower()}.comment\n\n')

ofile.write(f"feedback.pl -exp '{args.expname.lower()}' -jss '{args.jss.lower()}'\n\n")
ofile.write(f"firefox {args.expname.lower()}.html\n\n")

ofile.write(f"# Update the authentifications:\n")
ofile.write(f"http://archive.jive.nl/scripts/pipe/admin.php\n\n")

ofile.write("su jops\n\n")
ofile.write('archive -pipe -e {0}_{1}\n\n'.format(args.expname.lower(), obsdate.strftime('%y%m%d')))
ofile.write(f"cd $IN/{args.expname.lower()}\n\n")
ofile.write('archive -pipe -e {0}_{1}\n\n'.format(args.expname.lower(), obsdate.strftime('%y%m%d')))
ofile.write("exit\n\n")

ofile.write("# Put the pipeline results from calibrators into the db (from $OUT/exp)\n")
ofile.write(f"ampcal.sh\n\n\n")

ofile.write("# Back to ee\n\n")
ofile.write("Send PI letter to PI (CC jops)\n")
ofile.write("Send pipe letter to PI\n\n")
ofile.write(f"# Update the db with the pi letter information (BE CAREFUL WITH THE DATE, ONLY SESSION):\n")
if obsdate.month < 4:
    ofile.write(f"parsePIletter.py -s feb{obsdate.strftime('%y')} {args.expname.lower()}.piletter\n\n\n")
elif obsdate.month < 9:
    ofile.write(f"parsePIletter.py -s jun{obsdate.strftime('%y')} {args.expname.lower()}.piletter\n\n\n")
else:
    ofile.write(f"parsePIletter.py -s oct{obsdate.strftime('%y')} {args.expname.lower()}.piletter\n\n\n")

ofile.write(f"Done!\n\n\n")


ofile.close()

print(f'{args.o} has been successfully created.')

