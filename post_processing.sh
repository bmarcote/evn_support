#! /bin/zsh

function post_process_eee() {
    # Three parameters are expected:
    #	- The experiment name (case insensitive).
    #	- The reference station to use in standardplots.
    #	- The calibrators to use in standardplots.
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

    # Creating the experiment directory in /data0/marcote/EXP and moving to it
    e $EXP

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

    gv ${exp}-weight.ps
    ls ${exp}-auto*ps | parallel 'gv {}'
    ls ${exp}-cross*ps | parallel 'gv {}'
    ls ${exp}-ampphase*ps | parallel 'gv {}'


    read -q "REPLY?Please, update the PI letter. Do you want to continue? (y/n) "
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


    read -q "REPLY?If you need to PolConvert, DO IT NOW. Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    gzip *ps
    archive -auth -e ${exp}_${date} -n ${exp} -p ${pass}
    archive -stnd -e ${exp}_${date} ${exp}.piletter *ps.gz
    archive -fits -e ${exp}_${date}  *IDI*

    pipelet.py ${exp} marcote

    echo '\n\nWork at eee finished.\n'
}


function archive_pipeline() {
    # First argument should be experiment name (lower cases) second one date (YYMMDD)
    cd $IN/$1
    archive -pipe -e ${1}_${2}
    cd $OUT/$1
    archive -pipe -e ${1}_${2}
}

function post_process_pipe() {
    # Three parameters are expected:
    #	- The experiment name (case insensitive).
    #	- The session (in mmmYY format e.g. feb18)
    # This script should be run from the experiment folder.
    if [[ ! ( -n $1 && -n $2 ) ]];then
        echo "Two parameters are required:"
        echo " - experiment name (case insensitive)."
        echo " - Observing date (in mmmYY format e.g. feb18)."
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


    # Create all the required directories and move to marcote/exp one
    em ${exp}
    vlbeerexp $2 ${exp}

    read -q "REPLY?Do you have all ANTAB files? Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    uvflgall.csh
    antab_check.py

    read -q "REPLY?Have you fixed all ANTAB files? Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    cat ${exp}*.antabfs > ${exp}.antab
    cat ${exp}*.uvflgfs > ${exp}.uvflg
    cp ${exp}.antab $IN/${exp}/
    cp ${exp}.uvflg $IN/${exp}/
    cd $IN/${exp}

    # Input file and minimal modifications
    cp ../template.inp ${exp}.inp.txt
    replace "userno = 3602" "userno = ${give_me_next_userno.sh}" -- ${exp}.inp.txt
    replace "experiment = n05c3" "experiment = ${exp}" -- ${exp}.inp.txt

    echo "You should now edit the input file and run the EVN pipeline by your own.\n"
    read -q "REPLY?Do you want to continue (pipeline properly finished)? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    cd $OUT/${exp}
    comment_tasav_file.py ${exp}
    feedback.pl -exp '${exp}' -jss 'marcote'
    echo "You may need to modify the comment file and/or run again feedback.pl\n"

    read -q "REPLY?You may want to archive the pipeline results and protect them afterwards. (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'
    # su jops -c "archive_pipeline ${exp} ${date}"
    ampcal.sh

}


if [[ "$(hostname)" = "eee2" ]];then
    echo "We are in eee2!"
    post_process_eee $1 $2 $3
elif [[ "$(hostname)" = "jop83" ]];then
    echo "We are in pipe!"
    post_process_pipe $1 $2
    echo '\n\nWork at pipe finished. You may want to distribute the experiment!\n'
else
    echo "We are somewhere else!"
    if [[ ! ( -n $1 && -n $2 && -n $3 && -n $4 ) ]];then
        echo "Four parameters are required:"
        echo " - experiment name (case insensitive)."
        echo " - Reference station to be used for the plots and pipeline."
        echo " - Calibrators to be used for the standardplots."
        echo " - Observing date (in mmmYY format e.g. jan18)."
        exit
    fi
    # Three parameters are expected:
    #	- The experiment name (case insensitive).
    #	- The reference station to use in standardplots.
    #	- The calibrators to use in standardplots.
    #	- The session (in mmmYY format e.g. feb18)
    ssh jops@eee -t "HOME=/data0/marcote/;zsh" "post_processing.sh $1 $2 $3"
    ssh pipe@jop83 -t "setenv HOME /jop83_0/pipe/in/marcote;post_processing.sh $1 $4"
    ssh jops@jop83 "archive_pipeline ${exp} ${date}"
    echo '\n\nWork finished. You may want to distribute the experiment!\n'
fi


