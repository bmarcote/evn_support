#!/usr/bin/env python3

import os
import sys
import configparser
import subprocess
import datetime
import jplotter
import command

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
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process != 0:
        raise ValueError(f"\nError code {process} when running scp {originpath} {destpath}.")


def get_vixfile(expname: str):
    """Copies the .vix file from ccs to the current directory for the given expname.
    """
    scp(f"jops@ccs:/ccs/expr/{expname}/{expname.lower()}.vix", '.')
    os.symlink(f"{expname.lower()}.vix", f"{expname.upper()}.vix")
    print('Vix file copied to the current directory.')


def copy_cor_file(expname: str, scanno: str, date: str):
    """Copies the correlation file produced by a local correlation during an NME for the experiment
    name 'expname' and for the scan number 'scanno' to the current directory.
    - Inputs
        expname : experiment name (case-insensitive)
        scanno : str with the scan number to be processed as expected from the syntax 'scan{scanno}.cor'.
        date : date for the given experiment in the form YYYY_month, where month is the full name of the month.
    """
    scp(f"jops@tail.sfxc:/home/jops/sfxc/ftp/{date}/{expname.lower()}/output/scan{scanno}.cor", ".")


def j2ms2(expname: str, scanno: str):
    """Runs j2ms2 in the retrieved correlation file called 'scan{scanno}.cor' and produces the
    '{expname}-scan{scanno}.ms' file. If this MS file already exists, it will be removed.
    expname is case insensitive.
    """
    msfile = f"{expname.lower()}-scan{scanno}.ms"
    if os.path.isdir(msfile):
        process = subprocess.call(["rm", "-rf", f"{msfile}"], shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)

    subprocess.call(["j2ms2", "-o", msfile, f"scan{scanno}.cor"], shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)


def standardplots(expname: str, scanno: str, refant: str):
    """Runs standardplots to create auto- and cross- correlations during an NME for the specified
    experiment (expname; case insensitive) and scan number, expecting a MS in the current directory called
       {expname.lower()}-scan{scanno}.ms
    """
    def open_ms(expname, scanno):
        yield f"ms {expname.lower()}-scan{scanno}.ms"
        yield "indexr"

    def auto_plots():
        yield "bl auto"
        yield "fq */p"
        yield "pt ampchan"
        yield "ch none"
        yield "avc none"
        yield "avt vector"
        yield "ckey p['RR']=2 p['LL']=3 p['RL']=4 p['LR']=5 p[none]=1"
        yield "sort bl sb"
        yield "new sb false"
        yield "multi true"
        yield "nxy 1 4"
        yield "y 0 1.8"
        yield "pl"

    def cross_plots():
        yield f"bl {refant}* -auto"
        yield "fq *"
        yield "pt ampchan"
        yield "ch none"
        yield "avc none"
        yield "avt vector"
        yield "ckey p['RR']=2 p['LL']=3 p['RL']=4 p['LR']=5 p[none]=1"
        yield "sort bl sb"
        yield "new sb false"
        yield "multi true"
        yield "nxy 1 4"
        yield "y local"
        yield "pl"

    todo = [open_ms(expname, scanno), auto_plots(), cross_plots()]
    jplotter.run_plotter(command.scripted(*todo))



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
        nme_date = args.date
    else:
        nme_date = datetime.datetime.today().strftime('%Y_%B').lower()

    get_vixfile(args.expname)
    copy_cor_file(args.expname, args.scan_number, nme_date)
    j2ms2(args.expname, args.scan_number)
    standardplots(args.expname, args.scan_number, args.refant)











