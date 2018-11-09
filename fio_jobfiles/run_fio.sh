#!/bin/sh
set -ux

if [ "$FIO_JOB" = "write" ]
then export DATA_DIR=/data/fio_write/$POD_NAME
else export DATA_DIR=/data/fio_read; fi
mkdir -p $DATA_DIR
export JOB_DIR=/data/$JOB_NAME
export RESULT_DIR=$JOB_DIR/$POD_NAME
mkdir -p $RESULT_DIR
echo $POD_NAME >> $JOB_DIR/0.lock
while [ $(cat $JOB_DIR/0.lock | wc -l) -le $NUM_PODS ]; do usleep 1000; done
let i=128; let lim=16*1024*1024
while [ $i -le $lim ]; do
  echo $i
  fio /fio_jobfiles/global_config.fio --fallocate=none --runtime=30 --directory=$DATA_DIR --output-format=json+ --blocksize=$i --output=$RESULT_DIR/$i.json
  echo $POD_NAME >> $JOB_DIR/$i.lock
  while [ $(cat $JOB_DIR/$i.lock | wc -l) -le $NUM_PODS ]; do usleep 1000; done
  let i=2*i
done
rm $JOB_DIR/*.lock
if [ "$FIO_JOB" = "write" ]; then rm -rf $DATA_DIR; fi
chown -R ${RESULT_USER:-1000}:${RESULT_GROUP:-1000} $RESULT_DIR
