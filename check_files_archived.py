#! /usr/bin/env python

"""Checks that all FITS IDI files from the given experiment are accessible
by the EVN Pipeline (they have been archived properly).

This script will avoid a potential problem when the files have been archived
from eee (i.e. moved to the temporary directory in jop83) but still not fully
moved to its final destination in the archive.
If the Pipeline is executed in between those two states, it will run without
showing isses but using only part of the observation.

Version: 1.0
Date: 12 February 2020
Written by Benito Marcote (marcote@jive.eu)
"""
import sys
import time
import datetime
import subprocess


def check(expname):
    # Get the number of files and sizes from the IDI files in eee
    eee_call = ["ssh", "jops@eee", "du", "-ac", f"/data0/\*/{expname.upper()}/\*IDI\*"]
    # The output will contain N+1 lines. N files plus the total size in the last one
    pipe_call = ["du", "-ac", f"/jop83_1/archive/exp/*{expname.upper()}*/fits/*IDI*"]

    # To be done only once
    output_eee = subprocess.Popen(' '.join(eee_call), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf-8')

    files_eee = [outi.split('\t') for outi in output_eee.split('\n') if outi != '']
    # [ [ifile_size, ifile_path], ..., [total_size, 'total'] ]

    # Loop and sleep in pipe if files not ready
    # It waits for intervals of 1, 5, 10, 10, 30, 60, 120 min.
    for add_interval in (1, 5, 10, 10, 30, 60, 120):
        output_pipe = subprocess.Popen(' '.join(pipe_call), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf-8')

        files_pipe = [outi.split('\t') for outi in output_pipe.split('\n') if outi != '']

        # Check number of files and sizes
        # Allow 10% margin as different definitions of 1000/1024..
        if len(files_eee) == len(files_pipe):
            if abs(float(files_eee[-1][0])/float(files_pipe[-1][0])-1.0) < 0.005:
                print('All FITS IDI files are properly archived and the EVN Pipeline will run now.\n')
                return True
        
        print('{} - Sleeping for {} min before checking again if files are available.'.format(datetime.datetime.now().strftime('%H:%M'), add_interval))
        time.sleep(add_interval*60)
        if add_interval == 120:
            print('Exiting. Please try to run the EVN Pipeline again in the future.')
            return False



if __name__ == '__main__':
    check(sys.argv[1].strip())


