#!/usr/bin/python3
import sys, os
import datetime as dt

if len(sys.argv) < 3:
    print('Modifies an ANTAB file to write more Tsys values when the time separation between them is too long.\n')
    print('antabfs_interpolate.py antabfile timeinterval\n')
    print(' - antabfile: the antabfs file to modify (it will be replaced)')
    print(' - timeinterval: interval (in seconds) between Tsys that you wish')
    sys.exit(1)
else:
    filepath = sys.argv[1]
    timeinterval = dt.timedelta(seconds=int(sys.argv[2]))


thefile = open(filepath, 'r+')
newfile = open(filepath+'.tmp', 'wt')
lines = thefile.readlines()
# Remove comments
lines = [aline for aline in lines if aline[0] != '!']

def gettime(antabline):
    aline_array = antabline.split()
    # DOY TIME TSYS1..n
    intime_doy = aline_array[0]
    intime_hhmm, intime_ss = aline_array[1].split('.')
    intime_ss = float('0.'+intime_ss)*60
    intime = ' '.join([intime_doy, '{}:{}'.format(intime_hhmm, int(intime_ss))])
    return dt.datetime.strptime(intime, '%j %H:%M:%S')


for index,aline in enumerate(lines):
    if aline[0].isdigit():
        # Then this line is a Tsys input
        newfile.write(aline)
        if lines[index+1][0].isdigit():
            # If it is not the last line append new lines
            time1 = gettime(aline)
            time2 = gettime(lines[index+1])
            # Interpolate lines
            timei = time1 + timeinterval
            while timei < time2:
                newline = aline.split()
                newline[0] = timei.strftime('%j')
                newline[1] = timei.strftime('%H:%M') + '.' + str(int(timei.second/.6))
                # For now, we just duplicate the Tsys values at time1 until time2.
                newfile.write(' '.join(newline)+'\n')
                timei += timeinterval
    else:
        # Then is a line containing information or a comment or... NO a Tsys mesurement
        newfile.write(aline)





thefile.close()
newfile.close()
os.rename(filepath+'.tmp', filepath)

print('The antab file was updated.')


