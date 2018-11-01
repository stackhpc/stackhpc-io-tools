#!/bin/bash

test_dir=/alaska/stig/stackhpc-io-tools
test_clients=$*
test_dataset_files=8
test_dataset_file_gb=8

for i in $test_clients
do 
    # Create test directories, one per client
    datadir=$test_dir/fio_datafiles/$i
    mkdir -p $datadir

    for ((j=0; j < $test_dataset_files; j=$j+1))
    do
        datafile=$datadir/$j.dat

        if [[ -f $datafile ]]
        then
            datafile_bytes=$(stat -c '%s' $datafile)
            if [[ "$datafile_bytes" = "$(($test_dataset_file_gb * 1024 * 1024 * 1024))" ]]
            then
                echo "Skipping generation of $datafile: already set up"
                continue
            fi
        fi

        # Write out a set of test files to each test directory
        dd if=/dev/zero of=$datafile bs=1G count=$test_dataset_file_gb
    done
done
