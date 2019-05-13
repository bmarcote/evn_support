#!/usr/bin/env python3
"""
Splits a key file that contains multiple experiments to create single-experiment
key files.


Usage: keyfile_split.py keyfile
Options:
    keyfile : str          Path to the key file to be imported


Version: 0.0
Date: Feb 2019
Written by Benito Marcote (marcote@jive.eu)
"""

import sys
import argparse
import numpy as np
# from pyrap import tables as pt


help_keyfile = 'keyfile to be read'
help_v = 'Print more detailed log messages'
help_experiments = """In case you want to explicitely especify the experiments to process,
which can be a subset of all experiments available in the keyfile.
"""

usage = "%(prog)s [-h] <keyfile>"
description="""Splits a key file that contains multiple experiments to create single-experiment
key files. By default the new files to be created will be named as keyfile-##.key

The following things must be properly set up in the keyfile:
- A line as:
    expt = 'e-EVN: exp1, exp2, ...'  where exp1, exp2, ... are the experiment names.
    or
    expt = 'exp1, exp2, ...'  where exp1, exp2, ... are the experiment names.

- Inside srccat, sources from different experiments must be separated by a comment line as:
    ! EXPNAME {following words are accepted after a space character}

"""
parser = argparse.ArgumentParser(description=description, prog='keyfile_split.py', usage=usage)
parser.add_argument('keyfile', type=str, help=help_keyfile)
parser.add_argument('--version', action='version', version='%(prog)s 0.0')
parser.add_argument("-v", "--verbose", default=True, action="store_false" , help=help_v)
parser.add_argument('-e', '--experiments', default=None,type=str, help=help_experiments)

arguments = parser.parse_args()

verbose = arguments.verbose


exps = {} # Names with all experiments included in the keyfile

class Keyfile:
    def __init__(self, expcode):
        self.expcode = expcode
        self.lines = []

    def write_keyfile(self, outputname):
        # Update the expcode in the lines, including such line after the version one.
        f = open(outputname, 'w')
        # f.writelines()


# Required functions
def get_experiments(exptline):
    """Receives a line like:  expt = 'e-EVN: exp1, exp2, ...' or expt = 'exp1, exp2, ...'
    and returns a list with all experiments (e.g. exp1, exp2, ...).
    """
    exptline = exptline.strip().replace("'", '')
    if ':' in exptline:
        exptline = exptline.split(':')[1]
    else:
        exptline = exptline.split('=')[1]

    return [i.strip() for i in exptline.split(',')]



class Checks():
    self.experiments = False
    # self.


with open(arguments.keyfile, 'r').readlines() as key:
    in_srccat = False
    for i,aline in enumerate(key):
        if ('expt = ' in aline) or ('expt=' in aline):
            experiments = get_experiments(exptline)
            # Create a Keyfile for each experiment, saving all previous lines (up to now)
            if arguments.experiments is not None:
                for an_exp in arguments.experiments:
                    assert an_exp in experiments
                    exps[an_exp] = Keyfile(an_exp)
            else:
                for an_exp in experiments:
                    exps[an_exp] = Keyfile(an_exp)

            for an_exps in exps:
                for a_past_line in key[:i]:
                    exps[an_exps].lines.append(a_past_line)
            # Update checks?

        if 'srccat' in aline:
            in_srccat = True
            for an_exps in exps:
                exps[an_exps].lines.append(aline)

            inside_exp = None
            for srcline in key[i+1:]:
                if 'endcat' in srcline:
                    in_srccat = False
                    break

                if '! ' in srcline:  # do a better comparison for the names !!!!!!!!!!!!!!
                    inside_exp = srcline.replace('!','').strip().split(' ')[0]
                else:
                    if inside_exp is None:
                        for an_exps in exps:
                            exps[an_exps].lines.append(srcline)
                    else:
                        exps[inside_exp].lines.append(srcline)

        if in_srccat:
            continue


        else:
            for an_exps in exps:
                exps[an_exps].lines.append(srcline)






