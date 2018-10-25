#!/bin/bash

result_dir=fio-results-$(date '+%F-%T')

read_random_result_dir=$result_dir/read-random
mkdir -p $read_random_result_dir
for ((i=128; i <= $((16*1024*1024)); i=$i*2))
do
    echo $i
    fio fio-jobfiles/read-random.fio --runtime=30 --directory=$PWD/fio-datafiles/openhpc-login-0 --output-format=json+ --blocksize=$i > $read_random_result_dir/read-random-$i.json
done

