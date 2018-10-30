#!/bin/sh
export WORK_DIR=/data/read-random/$JOB_NAME
mkdir -p $WORK_DIR
let i=128
let lim=16*1024*1024
while [ $i -le $lim ]
do
    echo $i
    fio fio-jobfiles/read-random.fio --runtime=30 --output-format=json+ --blocksize=$i > $WORK_DIR/$i.json
    let i=2*i
done

rm $WORK_DIR/*.dat
