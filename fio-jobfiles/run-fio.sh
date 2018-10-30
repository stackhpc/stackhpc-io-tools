#!/bin/sh

result_dir=/data/fio-$(date '+%F-%T')

read_random_result_dir=$result_dir/read-random
mkdir -p $read_random_result_dir
i=128
let lim=16*1024*1024
while [ $i -le $lim ]
do
    echo $i
    fio fio-jobfiles/read-random.fio --runtime=30 --output-format=json+ --blocksize=$i > $read_random_result_dir/read-random-$i.json
    let i=2*i
done

