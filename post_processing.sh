#! /bin/zsh
# Three parameters are expected:
#	- The experiment name (case insensitive).
#	- The reference station to use in standardplots.
#	- The calibrators to use in standardplots.
# This script should be run from the experiment folder.

if [[ ! ( -n $1 && -n $2 && -n $3 ) ]];then
	echo "Three parameters are required:"
	echo " - experiment name (case insensitive)."
	echo " - Reference station to be used for the plots."
	echo " - Calibrators to be used for the plots."
	exit
fi

exp=$1
exp=${(L)1}
EXP=${(U)1}

date=${ssh jops@ccs grep EC067A /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 3}
# In the case of eEVN with an experiment name different this method may not work
if [[ -n $date ]];then
	date=${ssh jops@ccs grep EC067A /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 4}
fi

# Sometimes it has a \n or empty spaces.
date=${${${date}:s/"\\n"/""}:s/" "/""}

echo 'Processing experiment ${EXP}_${date}.\n'


# Create the lis file from ccs
ssh jops@ccs "cd /ccs/expr/${EXP};/ccs/bin/make_lis -e ${EXP} -p prod -s ${exp}.lis"

scp jops@ccs:/ccs/expr/${EXP}/${exp}.vix ./${exp}.vix
scp jops@ccs:/ccs/expr/${EXP}/${exp}.lis ./${exp}.lis

scp jops@jop83:piletters/${exp}.piletter .
scp jops@jop83:piletters/${exp}.expsum .

ln -s ${exp}.vix ${EXP}.vix

checklis ${exp}.lis

read -q "REPLY?Are you happy with this lis file? (y/n) "
if [[ ! $REPLY == 'y' ]];then
	exit
fi
echo '\n'

getdata.pl -proj ${EXP} -lis ${exp}.lis

j2ms2 -v ${exp}.lis

standardplots -weight ${exp}.ms $2 $3


read -q "REPLY?Check the standard plots. Do you want to continue? (y/n) "
if [[ ! $REPLY == 'y' ]];then
	exit
fi
echo '\n'


ysfocus.py ${exp}.ms

read -q "THRESHOLD?Which weight threshold should be applied to the data? "
echo '\n'

flag_weights.py ${exp}.ms $THRESHOLD

tConvert ${exp}.ms ${exp}_1_1.IDI

export pass=$(date | md5sum | cut -b 1-12)
touch ${exp}_${pass}.auth

gzip *ps
archive -auth -e ${exp}_${date} -n ${exp} -p ${pass}
archive -stnd -e ${exp}_${date} ${exp}.piletter *ps.gz
archive -fits -e ${exp}_${date}  *IDI*



