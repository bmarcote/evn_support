#!/usr/bin/env python3

import os
import sys
import tempfile
import argparse
import subprocess
import datetime


__version__ = 1
__prog__ = 'nme_standardplots.py'
usage = "%(prog)s [-h]  <experiment_name>  <scan_number>\n"
description = """Produces auto- and cross- correlations from a .cor file produced during a NME.
This program retrieves the .cor file expected to be located in jops@tail.sfxc that has been produced manually from a support scientist during a NME. Then it creates the associated MS file and runs jplotter to produce the plots.

The program assumes that the experiment is being conducted today (at the time of the call to this script).
Otherwise, you may need to specify the date with the '-d' or '--date' option.
"""




def scp(originpath, destpath):
    """Does a scp from originpath to destpath. If the process returns an error,
    then it raises ValueError.
    """
    process = subprocess.call(["scp", originpath, destpath], shell=False,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
    if process != 0:
        raise ValueError(f"\nError code {process} when running scp {originpath} {destpath}.")


def get_vixfile(expname: str):
    """Copies the .vix file from ccs to the current directory for the given expname.
    """
    if not os.path.isfile(f"{expname.lower()}.vix"):
        scp(f"jops@ccs:/ccs/expr/{expname.upper()}/{expname.lower()}.vix", '.')
        print('Vix file copied to the current directory.')

    if not os.path.isfile(f"{expname.upper()}.vix"):
        os.symlink(f"{expname.lower()}.vix", f"{expname.upper()}.vix")
        print('Symbolic link created to vix file.')

    # Because j2ms2 will search for a vix file named as the current directory
    pwd = os.getcwd().split('/')[-1]
    if not os.path.isfile(f"{pwd}.vix"):
        os.symlink(f"{expname.lower()}.vix", f"{pwd}.vix")



def copy_cor_file(expname: str, scanno: str, date: str):
    """Copies the correlation file produced by a local correlation during an NME for the experiment
    name 'expname' and for the scan number 'scanno' to the current directory.
    - Inputs
        expname : experiment name (case-insensitive)
        scanno : str with the scan number to be processed as expected from the syntax 'scan{scanno}.cor'.
        date : date for the given experiment in the form YYYY_month, where month is the full name of the month.
    """
    scp(f"jops@tail.sfxc:/home/jops/sfxc/ftp/{date}/{expname.lower()}/output/scan{scanno}.cor", ".")
    print(f"Correlation file 'scan{scanno}.cor' copied from tail.sfxc.")


def j2ms2(expname: str, scanno: str):
    """Runs j2ms2 in the retrieved correlation file called 'scan{scanno}.cor' and produces the
    '{expname}-scan{scanno}.ms' file. If this MS file already exists, it will be removed.
    expname is case insensitive.
    """
    msfile = f"{expname.lower()}-scan{scanno}.ms"
    if os.path.isdir(msfile):
        print("Removing existing MS file.")
        process = subprocess.call(["rm", "-rf", msfile], shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, bufsize=1)

    print("Running j2ms2...")
    process = subprocess.Popen(f"j2ms2 -o {msfile} scan{scanno}.cor", shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while process.poll() is None:
        out = process.stdout.readline().decode('utf-8')
        sys.stdout.write(out)
        sys.stdout.flush()

    print(f"MS file '{msfile}' created.")


def standardplots(expname: str, scanno: str, refant: str):
    """Runs standardplots to create auto- and cross- correlations during an NME for the specified
    experiment (expname; case insensitive) and scan number, expecting a MS in the current directory called
       {expname.lower()}-scan{scanno}.ms
    """
    def open_ms(expname, scanno):
        tmp = tempfile.NamedTemporaryFile()
        return f"ms {expname.lower()}-scan{scanno}.ms;refile {tmp.name};indexr"

    def auto_plots(expname, scanno):
        todo = ["bl auto"]
        todo += ["fq */p"]
        todo += ["pt ampchan"]
        todo += ["ch none"]
        todo += ["avc none"]
        todo += ["avt vector"]
        todo += ["ckey p[RR]=2 p[LL]=3 p[RL]=4 p[LR]=5 p[none]=1"]
        todo += ["sort bl sb"]
        todo += ["new sb false"]
        todo += ["multi true"]
        todo += ["nxy 1 4"]
        todo += ["y 0 1.8"]
        todo += [f"refile {expname.lower()}-scan{scanno}-auto.ps/cps"]
        todo += ["pl"]
        return ';'.join(todo)

    def cross_plots(expname, scanno, refant):
        todo = [f"bl {refant}* -auto"]
        todo += ["fq *"]
        todo += ["pt ampchan"]
        todo += ["ch none"]
        todo += ["avc none"]
        todo += ["avt vector"]
        todo += ["ckey p[RR]=2 p[LL]=3 p[RL]=4 p[LR]=5 p[none]=1"]
        todo += ["sort bl sb"]
        todo += ["new sb false"]
        todo += ["multi true"]
        todo += ["nxy 1 4"]
        todo += ["y local"]
        todo += [f"refile {expname.lower()}-scan{scanno}-cross.ps/cps"]
        todo += ["pl"]
        return ';'.join(todo)

    for afile in (f"{expname.lower()}-scan{scanno}-auto.ps", f"{expname.lower()}-scan{scanno}-cross.ps"):
        if os.path.isfile(afile):
            print("Removing existing plot files...")
            # process = subprocess.Popen(["rm", "-f", f"{afile}"], shell=True, stdout=subprocess.PIPE,
            process = subprocess.Popen(f"rm -f {afile}", shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, bufsize=1)

    todo = [open_ms(expname, scanno), auto_plots(expname, scanno), cross_plots(expname, scanno, refant)]
    print("Running jplotter...")
    print(f"\n\njplotter -c {';'.join(todo)}\n\n")
    process = subprocess.Popen(f"jplotter -c '{';'.join(todo)}'", shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, bufsize=1)
    while process.poll() is None:
        out = process.stdout.readline().decode('utf-8')
        sys.stdout.write(out)
        sys.stdout.flush()

    print("Plots produced and saved.")


if __name__ == '__main__':
    # Input parameters
    parser = argparse.ArgumentParser(description=description, prog=__prog__, usage=usage,
                                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('expname', type=str, help='Name of the EVN experiment (case insensitive).')
    parser.add_argument('scan_number', type=str,
                        help='Correlated scan number (as given in the <scan{scan_number}.cor> file name).')
    parser.add_argument('-d', '--date', type=str, default=None,
                        help='Date of the NME, given as YYYY_month, with month the full name of the month.')
    parser.add_argument('-r', '--refant', type=str, default='Ef',
                        help='Reference antenna to make plots. By default it is Ef.')
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    args = parser.parse_args()
    if args.date is None:
        nme_date = datetime.datetime.today().strftime('%Y_%B').lower()
    else:
        nme_date = args.date

    get_vixfile(args.expname)
    copy_cor_file(args.expname, args.scan_number, nme_date)
    j2ms2(args.expname, args.scan_number)
    standardplots(args.expname, args.scan_number, args.refant)











