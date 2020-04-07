#!/usr/bin/env python3
### --- scale1bit.py --- ####
### JMB Oct 2018 ###
### TACL by HV Oct 2018 ###
### Scales 1 bit data to account for quantization loss factors    

import pyrap.tables
import math
import argparse
import sys #for exit
import os.path

#old glish comments for safekeeping
# value of factor updated 20nov2015:  \sqrt{(pi/2)/1.1329552}
###  1.1329552 = 2bit-2bit correction factor already present in SFXC output
###  pi/2 = what would be the case for 1bit-1bit data
###  \sqrt = to get to 2bit-1bit factor, which forms the basis for the
###     existing logic
##  factor := 1.17631;
##  factor := 1.177480083;


factor1b1b = math.pi /2.0 / 1.1329552
factor1b2b = math.sqrt(factor1b1b)

# debug function for feedback
def debug(*msg, **kwargs):
    if args.verbose:
        print (*msg, file=sys.stderr, **kwargs)


#handle command line arguments: ms, antenna

parser = argparse.ArgumentParser(description='Scale 1 bit data to correct quantization losses')
parser.add_argument('ms', help="The measurement set to be corrected")
parser.add_argument('ant',nargs='+', help="The antenna(s) to correct (space delimited)")
parser.add_argument('-v', '--verbose', help="Print debug information", action="store_true")
parser.add_argument('-u', '--undo', help="Undo a previous run, take care to specify the same stations!", action="store_true")
parser.add_argument('-w', '--scale-weights', help="Also scale the weights", dest='to_scale', default=['DATA'], action='append_const', const='WEIGHT')
args = parser.parse_args()

if not os.path.exists(args.ms):
    print("Error, no such ms found!")
    sys.exit(1)

try:
    # query antenna table to translate 1 or more antenna names into antenna id's
    aList   = list(pyrap.tables.taql("""SELECT ROWID() AS ANTENNAS FROM {table}::ANTENNA
                                      WHERE UPCASE(NAME) IN {0}""".format(
                                          list(map(str.upper, args.ant)),table=args.ms)
                                    ).getcol('ANTENNAS'))

except Exception as e:
    print(e, "AAAAAAAAAARGH we have no such dishes, abort fail die :'(")
    sys.exit(1)

debug("Antenna list:", aList)
# depending on length of the result, use "ANTENNAx == <id>" or "ANTENNAx IN [<id>, <id>,...]" 
# because "==" is faster than "IN [<id>]" when only one <id> is present
antcond = ("== {0[0]}".format if len(aList)==1 else "IN {0}".format)(aList)
# and let taql do the real work ...
factor1, factor2 = (factor1b1b, factor1b2b) if not args.undo else (1/factor1b1b, 1/factor1b2b)

scale_it = "{{0}} = {{0}} * IIF(apply.ant1bit AND apply.ant2bit, {factor1b1b}, {factor1b2b})".format(factor1b1b=factor1, factor1b2b=factor2).format

#to_scale = ['DATA'] + (['WEIGHT'] if args.scale_weights else [])

t = pyrap.tables.taql("""
    UPDATE {table}
    SET  {todo}
    FROM [SELECT ANTENNA1 {condition} AS ant1bit, ANTENNA2 {condition} AS ant2bit
          FROM {table} GIVING AS memory] apply
    WHERE ((apply.ant1bit OR apply.ant2bit) and ANTENNA1 != ANTENNA2)
""".format(condition=antcond, table=args.ms, todo=",".join(map(scale_it, args.to_scale))))
