#!/bin/sh
set -ux

prepare () {
  if [ "$FIO_JOB" = "write" ]; then
    export SCRATCH_DIR=/data/fio_write/$POD_NAME
    mkdir -p $SCRATCH_DIR
  else
    export SCRATCH_DIR=/data/fio_read
  fi
  export JOB_DIR=/data/$JOB_NAME
  mkdir -p $JOB_DIR
  export JOB_LOCK="${JOB_DIR}/${FIO_JOB}.lock"
  if [ ! -f "$JOB_LOCK" ]; then
    for f in $(ls -I "${JOB_DIR}/*.lock"); do rm -rf $JOB_DIR/$f; done
    touch $JOB_LOCK
  fi
}

syncpods () {
  BS_LOCK=${JOB_DIR}/${1}.lock
  mkdir -p $BS_LOCK
  while [ $(ls $BS_LOCK | wc -l) -lt $NUM_PODS ]; do
    touch $BS_LOCK/$POD_NAME
    usleep 100000
  done
}

cleanup () {
  sleep 1; rm -rf $JOB_DIR/*.lock
  if [ "$FIO_JOB" = "write" ]; then rm -rf $SCRATCH_DIR; fi
  chown -R ${RESULT_USER:-1000}:${RESULT_GROUP:-1000} $RESULT_DIR
}

prepare
syncpods 0
export RESULT_DIR=$JOB_DIR/$POD_NAME
mkdir -p $RESULT_DIR
let bs=128; let lim=16*1024*1024
while [ $bs -le $lim ]; do
  echo $bs
  fio /fio_jobfiles/global_config.fio --fallocate=none --runtime=30 --directory=$SCRATCH_DIR --output-format=json+ --blocksize=$bs --output=$RESULT_DIR/$bs.json
  syncpods $bs
  let bs=2*bs
done
cleanup
