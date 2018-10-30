#!/bin/sh

result_dir=/data/read-random/${JOB_NAME}
mkdir -p $result_dir
let i=128
let lim=16*1024*1024
while [ $i -le $lim ]
do
    echo $i
    fio fio-jobfiles/read-random.fio --runtime=30 --output-format=json+ --blocksize=$i > $result_dir/$i.json
    let i=2*i
done

rm  /data/${JOB_NAME}-*.dat
