#!/bin/sh
export DATA_DIR=/data/fio_datafiles/k8s
export WORK_DIR=/data/$JOB_NAME/$POD_NAME
mkdir -p $WORK_DIR
let i=128
let lim=16*1024*1024
while [ $i -le $lim ]
do
    echo $i
    fio /fio_jobfiles/read_random.fio --runtime=30 --directory=$DATA_DIR --output-format=json+ --blocksize=$i > $WORK_DIR/$i.json
    let i=2*i
done
