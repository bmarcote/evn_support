#! /usr/bin/env zsh

function post_process_eee() {
    # Three parameters are experimentected:
    # - The experiment name (case insensitive).
    # - The reference station to use in standardplots.
    # - The calibrators to use in standardplots.
    # This script should be run from the experiment folder.
    if [[ ! ( -n $1 && -n $2 && -n $3 ) ]];then
        echo "Three parameters are required:"
        echo " - experiment name (case insensitive)."
        echo " - Reference station to be used for the plots."
        echo " - Calibrators to be used for the plots."
        exit
    fi

    export PATH=$PATH:/home/jops/scripts/:/home/jops/bin/:/home/jops/.local/bin:$PATH:/data0/marcote/scripts/evn_support/
    experiment=$(echo "${(L)1}")
    Experiment=$(echo "${(U)1}")

    epoch=$(ssh jops@ccs grep $Experiment /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 3)
    # In the case of eEVN with an experiment name different this method may not work
    if [[ ! -n $epoch ]];then
        epoch=$(ssh jops@ccs grep $Experiment /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 4)
    fi

    # Sometimes it has a \n or empty spaces.
    epoch=${${${epoch}:s/"\\n"/""}:s/" "/""}
    epoch=$(echo $epoch | cut -c3-)

    echo "Processing experiment ${Experiment}_${epoch}.\n"


    # Create the lis file from ccs
    ssh jops@ccs "cd /ccs/expr/${Experiment};/ccs/bin/make_lis -e ${Experiment} -p prod -s ${experiment}.lis"
    scp jops@ccs:/ccs/expr/${Experiment}/${experiment}.vix ./${experiment}.vix
    scp jops@ccs:/ccs/expr/${Experiment}/${experiment}.lis ./${experiment}.lis
    scp jops@jop83:piletters/${experiment}.piletter .
    scp jops@jop83:piletters/${experiment}.expsum .
    ln -s ${experiment}.vix ${Experiment}.vix

    checklis ${experiment}.lis

    read -q "REPLY?Are you happy with this lis file? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    getdata.pl -proj ${Experiment} -lis ${experiment}.lis

    j2ms2 -v ${experiment}.lis

    standardplots -weight ${experiment}.ms $2 $3

    gv ${experiment}-weight.ps
    ls ${experiment}-auto*ps | parallel 'gv {}'
    ls ${experiment}-cross*ps | parallel 'gv {}'
    ls ${experiment}-ampphase*ps | parallel 'gv {}'


    ysfocus.py ${experiment}.ms

    read "THRESHOLD?Which weight threshold should be applied to the data? "
    # echo '\n'

    flag_weights.py ${experiment}.ms $THRESHOLD

    read -q "REPLY?Please, update the PI letter. Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    tConvert ${experiment}.ms ${experiment}_1_1.IDI

    pass=$(date | md5sum | cut -b 1-12)
    touch ${experiment}_${pass}.auth


    read -q "REPLY?If you need to PolConvert, DO IT NOW. Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    gzip *ps
    archive.pl -auth -e ${experiment}_${epoch} -n ${experiment} -p ${pass}
    echo "Archiving..."
    archive.pl -stnd -e ${experiment}_${epoch} ${experiment}.piletter *ps.gz
    archive.pl -fits -e ${experiment}_${epoch}  *IDI*

    pipelet.py ${experiment} marcote

    echo '\n\nWork at eee finished.\n'
}


function archive_pipeline() {
    # First argument should be experiment name (lower cases) second one epoch (YYMMDD)
    cd $IN/$1
    su jops -c "/export/jive/jops/bin/archive/user/archive.pl -pipe -e ${1}_${2}"
    cd $OUT/$1
    su jops -c "/export/jive/jops/bin/archive/user/archive.pl -pipe -e ${1}_${2}"
}

function post_process_pipe() {
    # This script should be run from the experiment folder.
    if [[ ! ( -n $1 && -n $2 ) ]];then
        echo "Two parameters are required:"
        echo " - experiment name (case insensitive)."
        echo " - session (in mmmYY format e.g. feb18)."
        exit
    fi
    export PATH=$PATH:/home/jops/scripts/:/home/jops/bin/:/home/jops/.local/bin:$PATH:/data0/marcote/scripts/evn_support/
    source /jop83_0/pipe/in/marcote/.zshrc
    experiment=$(echo "${(L)1}")
    Experiment=$(echo "${(U)1}")

    epoch=$(ssh jops@ccs grep $Experiment /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 3)
    # In the case of eEVN with an experiment name different this method may not work
    if [[ ! -n $epoch ]];then
        epoch=$(ssh jops@ccs grep $Experiment /ccs/var/log2vex/MASTER_PROJECTS.LIS | cut -d " " -f 4)
    fi

    # Sometimes it has a \n or empty spaces.
    epoch=${${${epoch}:s/"\\n"/""}:s/" "/""}
    epoch=$(echo $epoch | cut -c3-)

    echo "Processing experiment ${Experiment}_${epoch}.\n"

    # Create all the required directories and move to marcote/experiment one
    em ${experiment}
    # vlbeerexp $2 ${experiment}

    read -q "REPLY?Do you have all ANTAB files? Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    # uvflgall.csh
    # antab_check.py

    read -q "REPLY?Have you fixed all ANTAB files? Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    # cat ${experiment}*.antabfs > "${experiment}.antab"
    # cat ${experiment}*.uvflgfs > "${experiment}.uvflg"
    # cp "${experiment}.antab" "$IN/${experiment}/"
    # cp "${experiment}.uvflg" "$IN/${experiment}/"
    cd "$IN/${experiment}"

    # Input file and minimal modifications
    cp ../template.inp ${experiment}.inp.txt
    replace "userno = 3602" "userno = $(give_me_next_userno.sh)" -- "${experiment}.inp.txt"
    replace "experiment = n05c3" "experiment = ${experiment}" -- "${experiment}.inp.txt"

    read -q "REPLY?You should now edit the input file. Do you want to continue? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'
    EVN.py ${experiment}.inp.txt
    read -q "REPLY?Do you want to continue (pipeline properly finished)? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'

    cd $OUT/${experiment}
    comment_tasav_file.py ${experiment}
    feedback.pl -exp "${experiment}" -jss 'marcote'
    echo "You may need to modify the comment file and/or run again feedback.pl\n"

    read -q "REPLY?Do you want to archive the pipeline results (protect them afterwards)? (y/n) "
    if [[ ! $REPLY == 'y' ]];then
        exit
    fi
    echo '\n'
    archive_pipeline ${experiment} ${epoch}
    ampcal.sh

    echo '\n\nWork at pipe finished. You may want to distribute the experiment!\n'
}


if [[ `hostname` == "eee2" ]];then
    echo "Executing steps from eee..."
    post_process_eee $1 $2 $3
elif [[ `hostname` == "jop83" ]];then
    echo "Executing steps from pipe..."
    post_process_pipe $1 $2
else
    echo "Computer not recognized."
fi



