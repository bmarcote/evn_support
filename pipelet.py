#!/usr/bin/env python3
"""
Creates the {exp}.pipelet.
Given the default template, customizes it to include the basic data from the given experiment.

Version: 1.0
Date: April 2019
Author: Benito Marcote (marcote@jive.eu)

"""
import os
import sys
import glob
import argparse
from datetime import datetime as dt


__version__ = 1.0
# The .comment file template is located in the same directory as this script. Or it should be.
template_pipelet_file = os.path.dirname(os.path.abspath(__file__)) + '/template.pipelet'

help_str = """Creates a .pipelet file in the current directory.

This letter is the content that must be sent to the PI after pipelining an experiment.
It contains information about the pipeline output and the credentials to access the data.
It takes the credentials from the username_password.auth file that should be placed in the current directory
(otherwise specify its file, or the username and password as parameters).

The user must provide the following information:
- The experiment name (case insensitive).
- Who are you (the Support Scientist). Type your surname.
"""

parser = argparse.ArgumentParser(description=help_str, prog='pipelet.py')
parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))
parser.add_argument('-o', '--output', type=str, default='.', help='Output directory where the file {experiment}.pipelet will be store (by default the current directory)')
parser.add_argument('-c', '--credentials', type=str, default=None, help='Auth file containing the username and password in its name (required if *.auth is not in current directory).')
parser.add_argument('-u', '--username', type=str, default=None, help='Username to access the data (required if no credential file exists)')
parser.add_argument('-p', '--password', type=str, default=None, help='Password to access the data (required if no credential file exists)')
parser.add_argument('experiment', type=str, default=None, help='Experiment name.')
parser.add_argument('jss', type=str, default='', help='JIVE Support Scientist doing the post-processing (your surname).')


args = parser.parse_args()


jss = {'marcote': 'Benito Marcote', 'immer': 'Katharina Immer', 'nair': 'Dhanya Nair', '': ''}



def get_credentials_from_filename(thefile):
    """Assumes that the file name is made of the form username_password[.auth]
    It thus can only contain one '_' character, which separates both sides.

    Returns the username, and password.
    """
    assert thefile.count('_') == 1
    return thefile.split('.')[0].split('_')


# One of the following conditions must be true
if args.credentials is not None:
    username, password = get_credentials_from_filename(args.credentials)
elif (args.username is not None) and (args.password is not None):
    username, password = args.username, args.password
elif ((args.username is not None) and (args.password is None)) or ((args.username is None) and (args.password is not None)):
    raise AttributeError('Both username and password must be passed, or none of them.')
else:
    credential_file = glob.glob('*.auth')
    if len(credential_file) == 0:
        raise AttributeError('No credential *.auth file found and not enough paramenters passed')
    elif len(credential_file) > 1:
        raise AttributeError('Multiple *auth files found. Please specify the one to be used.')
    username, password = get_credentials_from_filename(credential_file[0])


with open(template_pipelet_file, 'r') as template:
    full_text = template.read()
    full_text = full_text.format(expname=args.experiment.upper(), delimiter='-'*(41+len(args.experiment)),
                                 username=username, password=password, supsci=jss[args.jss])

    pipelet_file = open('{}/{}.pipelet'.format(args.output if args.output[-1] != '/' else args.output[:-1],
                                               args.experiment.lower()), 'w')
    pipelet_file.write(full_text)
    pipelet_file.close()
    print('\nFile {0}.pipelet created successfully in {1}/.'.format(args.experiment.lower(), args.output if args.output[-1] != '/' else args.output[:-1]))


