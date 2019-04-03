#!/usr/bin/env python3
"""
Creates a .comment file for the EVN Pipeline.
Given a default template, customizes it to include the basic data from the given experiment.
The script will ask you in the terminal about all the required inputs.

Version: 1.1
Date: April 2019
Author: Benito Marcote (marcote@jive.eu)

version 1.1 changes
- Now it takes the cutoff value info from the input file.
- Recognises if it is an expected cont/line experiment and change several lines on that.
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime as dt


__version__ = 1.1
# The .comment file template is located in the same directory as this script. Or it should be.
template_file = os.path.dirname(os.path.abspath(__file__)) + '/template.comment'

help_str = """Creates a .comment file for the EVN Pipeline.
Given a default template, customizes it to include the basic data from the given experiment.
The script will ask you in the terminal about all the required inputs.
"""

parser = argparse.ArgumentParser(description=help_str, prog='comment_file.py')
parser.add_argument('experiment', type=str, default=None, help='Experiment name. Note: in case of multiple passes write {exp}_number (e.g. ev100_1')
parser.add_argument('-o', '--output', type=str, default=None, help='Output directory where the file {experiment}.comment will be saved (by default in /jop83_0/pipe/out/{experiment})')
parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))


args = parser.parse_args()



def get_input_file_info():
    """Parse the observed sources from the pipeline input file (/jop83_0/pipe/in/{exp}/{exp}.inp.txt).
    It searches for the bandpass=, target= and phaseref= lines.

    Returns
        - refant : str
            The reference antenna
        - cutoff : int
            The SNR cutoff used in FRING.
        - bpass : list
            The bandpass calibrators and fringe finders used in the pipeline.
        - phaseref : list
            The phase referencing calibrators used in the pipeline. None if no phase referencing experiment.
        - target : list
            The targets. Should have the same dimension than the phaseref (unless it is not a phase
            referencing experiment).
    """
    with open('/jop83_0/pipe/in/{}/{}.inp.txt'.format(args.experiment.lower().split('_')[0],
                                       args.experiment.lower()), 'r') as inpfile:
        phaseref = None
        cutoff = 7
        target = None
        for inpline in inpfile.readlines():
            if 'refant' in inpline:
                refant = inpline.split('=')[1].strip().split(',')[0]
            if ('fring_snr' in inpline) and inpline[0].strip() != '#':
                cutoff = int(inpline.split('=')[1].strip())
            if 'bpass' in inpline:
                bpass = [i.strip() for i in inpline.split('=')[1].strip().split(',')]
            if ('phaseref' in inpline) and inpline[0].strip() != '#':
                phaseref = [i.strip() for i in inpline.split('=')[1].strip().split(',')]
            if ('target' in inpline) and inpline[0].strip() != '#':
                target = [i.strip() for i in inpline.split('=')[1].strip().split(',')]
            if ('sources' in inpline) and inpline[0].strip() != '#':
                if target is None:
                    target = [i.strip() for i in inpline.split('=')[1].strip().split(',')]

        if target is None:
            raise ValueError('No sources found for target (neither target or sources are defined in INP file')

    return refant, cutoff, bpass, phaseref, target


def parse_sources(bpass, phaseref, target):
    """Returns the sentences to be placed in the comment file concerning the observed sources
    """
    s = ''
    if phaseref is not None:
        assert len(phaseref) == len(target)
        for a_phaseref, a_target in zip(phaseref, target):
            s += 'The target source {} was calibrated using the phase-reference source {}.<br>\n'.format(
                                                                                     a_target, a_phaseref)
    else:
        if len(target) > 1:
            s += 'The target sources {} were directly fringe-fitted and bandpass calibrated.<br>\n'.format(
                                                                                        ', '.join(target))
        else:
            s += 'The target source {} was directly fringe-fitted and bandpass calibrated.<br>\n'.format(target[0])

    if len(bpass) == 1:
        keys = ('was', '')
    else:
        keys = ('were', 's')

    s += '{0} {1} also observed as calibrator{2} and fringe finder{2}.<br>\n'.format(', '.join(bpass), *keys)
    return s


def get_setup():
    """Get the observation setup from the {exp}.SCAN file created by the Pipeline:
    It takes the file {exp}.SCAN that should be in /jop83_0/pipe/out/{exp}/.

    Returns
        - freq : float (GHz)
            The central frequency of the observation.
        - datarate : float (Mbps)
            The datarate of the observation.
        - number_ifs : int
            Number of IFs or subbands.
        - bandwidth : float (MHz)
            The bandwidth of each IF or subband.
        - pols : int
            Number of polarizations:
            1 - single pol.
            2 - dual pol.
            4 - ful pol.
    """
    with open('/jop83_0/pipe/out/{}/{}.SCAN'.format(args.experiment.lower().split('_')[0],
                                       args.experiment.lower()), 'r') as scanfile:
        freq = None
        lastline = None
        for scanline in scanfile.readlines():
            lastline = scanline # It will be the last line at the end of the loop. DO NOT JUDGE ME!!!!
            # Getting the frequency and the number of polarizations
            # The line is like Freq = XXXX GHz  Ncor = X  No. vis = XXXX
            if 'Freq = ' in scanline:
                # freq, pols = [i for i in map([i.strip() for i in scanline.split('=')].__getitem__, ())
                temp = ' '.join(scanline.split('=')).split()
                freq = float(temp[1])
                if temp[2] == 'GHz':
                    pass
                elif temp[2] == 'MHz':
                    freq *= 1e-3
                elif temp[2] == 'kHz':
                    freq *= 1e-6
                elif temp[2] == 'Hz':
                    freq *= 1e-9
                else:
                    raise ValueError('Not units found in the Freq = XXX line inside the SCAN file')

                pols = int(temp[4]) # number of polarizations 2=  dual, 4 = full)
                assert pols in (1, 2, 4)

        if freq is None:
            raise IOError('The SCAN file does not contain a line with Freq = XXX')


        # The very last line (if not empty) is the last IF with Freq, BW, ch.Sep, and Sideband
        last_if = lastline.split()
        if len(last_if) == 6:
            # It contains the FQID value
            number_ifs = int(last_if[1])
            bandwidth = int(float(last_if[3])*1e-3)
        elif len(last_if) == 5:
            # It does not contain the FQID value
            number_ifs = int(last_if[0])
            bandwidth = int(float(last_if[2])*1e-3)
        else:
            ValueError('Unexpected number of parameters at the end of the SCAN file.')

        if pols == 1:
            datarate = number_ifs*bandwidth*2*2
        else:
            datarate = number_ifs*bandwidth*2*2*2

    return freq, datarate, number_ifs, bandwidth, pols


def parse_setup(exp, type_exp, freq, datarate, number_ifs, bandwidth, pols):
    """Returns the text to place in the comment file concerning the experiment setup.
    Inputs
        - exp : str
            Experiment name (e.g. n18l2 or EB032).
        - type_exp : str
            To options allowed: 'cont' or 'line', for continuum or spectral line passes, resp.
        - freq : float (GHz)
            The central frequency of the observation.
        - datarate : float (Mbps)
            The datarate of the observation.
        - number_ifs : int
            Number of IFs or subbands.
        - bandwidth : float (MHz)
            The bandwidth of each IF or subband.
        - pols : int
            Number of polarizations:
            1 - single pol.
            2 - dual pol.
            4 - ful pol.
    """
    # It gets the date of the experiment from the MASTER_PROJECTS.LIS file in ccsbeta
    date = subprocess.getoutput('ssh jops@ccsbeta grep {} /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 3'.format(exp.upper()))
    obsdate = dt.strptime(date, '%Y%m%d')
    if freq < 0.6:
        band = 'P'
    elif freq < 1.9:
        band = 'L'
    elif freq < 3.0:
        band = 'S'
    elif freq < 7.0:
        band = 'C'
    elif freq < 11.0:
        band = 'X'
    elif freq < 18.0:
        band = 'U'
    elif freq < 30:
        band = 'K'
    elif freq >= 30:
        band = 'Q'

    name_pols = {1: 'single', 2: 'dual', 4: 'full'}
    s = '{}. {}-band experiment observed on {}.\n'.format(exp.upper(), band, obsdate.strftime('%d %B %Y'))
    s += 'This is the {} pass data.<br>\n'.format('continuum' if type_exp == 'cont' else 'spectral line')
    s += 'The data rate was {} Mbps ({} x {} MHz subbands, {} polarization, two-bit sampling)<br>\n'.format(
            datarate, number_ifs, bandwidth, name_pols[pols])

    return s


def get_antennas():
    """Returns a list of all antennas participating in the experiment. It takes the information
    from the {exp}.DTSUM located in /jop83_0/pipe/out/{exp}/.
    """
    with open('/jop83_0/pipe/out/{}/{}.DTSUM'.format(args.experiment.lower().split('_')[0],
                                       args.experiment.lower()), 'r') as dtsumfile:
        list_antennas = []
        inside_array = False
        for dtline in dtsumfile.readlines():
            if inside_array:
                if '(' in dtline:
                    templine = dtline
                    # More antennas to get
                    while '(' in templine:
                        list_antennas.append(templine[templine.index('(')+1:templine.index(')')].strip())
                        templine = templine[templine.index(')')+1:]
                else:
                    # We are done
                    inside_array = False
            if 'Array name' in dtline:
                inside_array = True

    return list_antennas


def parse_antennas(list_antennas):
    """Returns the text to include in the comment file concerning the participating antennas
    """
    list_antennas = [ant.capitalize() for ant in list_antennas]
    return '{} stations participated: {}.<br>\n'.format(len(list_antennas), ', '.join(list_antennas))


def parse_line_info(type_exp):
    """Places a sentence in the comment file (in different locations) when it is a spectral line pass
    to warn that the solutions are expected to be better for continuum passes.
    """
    if type_exp == 'cont':
        return ''
    elif type_exp == 'line':
        return 'This is the spectral line pass data. Better solutions are expected in the continuum data.'
    else:
        raise ValueError('Only "cont" or "line" are values expected for type_exp.')


with open(template_file, 'r') as template:
    type_experiment = 'line' if args.experiment[-2:] == '_2' else 'cont'
    full_text = template.read()
    refant, fringe_cutoff, *all_sources = get_input_file_info()
    full_text = full_text.format(setup_header=parse_setup(args.experiment, type_experiment, *get_setup()),
                     sources_info=parse_sources(*all_sources),
                     station_info=parse_antennas(get_antennas()), fringe_cutoff=fringe_cutoff,
                     ref_antenna=refant, type_info=parse_line_info(type_experiment))
    if args.output is None:
        outputdir = '/jop83_0/pipe/out/{}'.format(args.experiment.lower().split('_')[0])
    else:
        outputdir = args.output if args.output[-1] != '/' else args.output[:-1]
    comment_file = open('{}/{}.comment'.format(outputdir, args.experiment.lower()), 'w')
    comment_file.write(full_text)
    comment_file.close()
    print('\nFile {0}.comment created successfully in {1}/.'.format(args.experiment.lower(), outputdir))


