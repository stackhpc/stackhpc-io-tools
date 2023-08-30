#!/bin/bash

hostname
df /mnt

BS=$1

source mpi_env.sh

export CLIENT_NAME=${CLIENT_NAME:-$HOSTNAME-$OMPI_COMM_WORLD_LOCAL_RANK}
export SCENARIO_DIR=$RESULTS_PATH/$SCENARIO-$FIO_RW/$OMPI_COMM_WORLD_SIZE-$OMPI_COMM_WORLD_LOCAL_SIZE
export CLIENT_DIR=$SCENARIO_DIR/$CLIENT_NAME

case $FIO_RW in
    read|randread)
        export SCRATCH_DIR=$DATA_PATH/fio_read;;
    write|randwrite)
        export SCRATCH_DIR=$DATA_PATH/fio_write/$CLIENT_NAME;;
esac

mkdir -p $SCENARIO_DIR $CLIENT_DIR $SCRATCH_DIR

fio global_config.fio --directory=$SCRATCH_DIR --output-format=json+ --blocksize=$BS --output=$CLIENT_DIR/${BS}.json >& fio-$OMPI_COMM_WORLD_SIZE-$OMPI_COMM_WORLD_LOCAL_SIZE-$CLIENT_NAME-$BS.dat
