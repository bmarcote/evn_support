#!/usr/bin/env python
#Prints the gaps between each scan for each telescope, along with a summary
#Supports python2.7 and python3.4
#V1.0 14/10/2016 JMB
from __future__ import print_function
#import numpy as np #np.array and nm.linspace
import argparse #command line parsing
import sys #for sys.exit()
from datetime import datetime,timedelta

#parse inputs
parser = argparse.ArgumentParser(description='List gaps for each telescope in a SCHED keyin file. Note, stations with continuous cal will be reported but have an asterix in front of them')
parser.add_argument('sum_file', help="the .sum file to read. Must have early as a 'bottom' sumitem or by itself (last)")
parser.add_argument('-e', '--early', help="seconds antenna must be on source before scan start to count as sufficient for tsys. Defaults to 11", type=int, default=11) 
args = parser.parse_args()

earlyTimes=[] #initialise empty list
inEarlySection=False #when reading file we start not in the slewing section


with open(args.sum_file,"rt") as infile: #open file
  for line in infile:
    if line.strip() == 'Bottom item is: Seconds antenna is on source before scan start.':
      inEarlySection = True #we are now reading the early section
    if inEarlySection:
        if line.strip().startswith('SCAN SUMMARY'):
          inEarlySection = False #maybe new page, maybe end of section

        if line.strip() == 'TIME RANGE OF RECORDINGS and TOTAL BYTES:':
          break #stop reading if we hit the next item in the sum file

        if line.strip().startswith('STOP UT'): #this line has telescope info (codes), we actually read this multiple times but it should not change I think so no biggie...
            telescopes=line.strip().split()
        try:
            if(line.strip()[0].isdigit()): #if first character is a digit we have a start time
                earlyTimes.append(line.strip().split())
        except IndexError:
            pass

if len(earlyTimes) == 0:
  #if we made it all the way through without finding the slew section it means that that info is not in the sum summary
  print ("early is not a sumitem in the summary file. Can not continue.")
  sys.exit(1)

telescopes=telescopes[2:] #cut out the parts that are not telescope names

earlyTimes = earlyTimes[1::2] #every second line
# print ('Time',end="     ")
# for scope in telescopes:
#   print (scope.rjust(5),end="")
# print()
# for line in earlyTimes:
#   print (line[1],end=" ")
#   for item in line[4:]:
#     print (item.rjust(5), end="")
#   print('')

# lots of loops now, first for each telescope. This could be easily optimised but I'm going to be lazy I think
for i,scope in enumerate(telescopes):
  #loop through the early times and keep track of gaps
  #print(earlyTimes[0][0] + '/' + (earlyTimes[0][1]))
  lastGap = (earlyTimes[0][0] + '/' + earlyTimes[0][1])
  foundGap = False
  continuousCal = ('O8', 'Ys', 'Ef', 'Ro', 'Jb', 'Tr')
  contStationText = ''
  if scope in continuousCal:
    contStationText = '*'
  for scan in earlyTimes:
    try:
      if float((scan[4+i])) >= args.early:
        #print (scope, map(int,scan[1].split(':')))
        currentTime=(scan[0]+'/'+scan[1])
        #print(lastGap, currentTime)
        tDiff = datetime.strptime(currentTime, '%j/%H:%M:%S') - datetime.strptime(lastGap, '%j/%H:%M:%S')
        if tDiff.total_seconds()/60.0 > 15.0:
          print("%s%s, %s to %s,  Interval = %.1f minutes" % (contStationText, scope, lastGap, currentTime,  (tDiff.total_seconds()/60)))
        lastGap = currentTime
        foundGap = True
    except ValueError:
      if (scan[4+i] == '---D'):
        currentTime=(scan[0]+'/'+scan[1])
        lastGap = currentTime
      else:
        pass


  currentTime=(scan[0]+'/'+scan[1])
  tDiff = datetime.strptime(currentTime, '%j/%H:%M:%S') - datetime.strptime(lastGap, '%j/%H:%M:%S')
  if tDiff.total_seconds()/60.0 > 15.0:
    print("%s%s, %s to %s,  Interval = %.1f minutes" % (contStationText, scope, lastGap, currentTime,  (tDiff.total_seconds()/60)))
  if foundGap == False:
    print ("No Tsys at all for %s" % scope)

print()
print("Stations with an * use continuous cal and can be ignored\n")
