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

echo $exp
echo $EXP

# Create the lis file from ccs
ssh jops@ccs "/ccs/expr/${EXP};make_lis -e ${EXP} -p prod -s ${exp}.lis"

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


