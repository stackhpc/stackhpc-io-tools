#!/bin/sh
set -ux

export CLIENT_NAME=${CLIENT_NAME:-$HOSTNAME}

prepare () {
  mkdir -p $SCENARIO_DIR
  mkdir -p $SCRATCH_DIR
  for F in $(ls -I "$SCENARIO_DIR/*.lock" $SCENARIO_DIR); do rm -rf $SCENARIO_DIR/$F; sleep 1; done
}

syncpods () {
  BS_LOCK=$SCENARIO_DIR/${1}.lock
  mkdir -p $BS_LOCK
  while [ $(ls $BS_LOCK | wc -l) -lt $NUM_CLIENTS ]; do
    touch $BS_LOCK/$CLIENT_NAME
    sleep 1
  done
  mkdir -p $CLIENT_DIR
}

cleanup () {
  sleep 1; rm -rf $SCENARIO_DIR/*.lock
  if [[ "${FIO_RW}" =~ "write" ]]; then rm -rf $SCRATCH_DIR; fi
  chown -R ${RESULT_USER:-1000}:${RESULT_GROUP:-1000} $CLIENT_DIR
}

SCRATCH_DIR=$DATA_PATH/fio_read && [[ "${FIO_RW}" =~ "write" ]] && SCRATCH_DIR=$DATA_PATH/fio_write/$CLIENT_NAME
export SCRATCH_DIR
export SCENARIO_DIR=$RESULTS_PATH/$SCENARIO_NAME/$NUM_CLIENTS
export CLIENT_DIR=$RESULTS_PATH/$SCENARIO_NAME/$NUM_CLIENTS/$CLIENT_NAME

prepare
syncpods 0
let BS=256; let LIM=16*1024*1024
while [ $BS -le $LIM ]; do
  echo $BS
  fio $FIO_JOBFILES/global_config.fio --directory=$SCRATCH_DIR --output-format=json+ --blocksize=$BS --output=$CLIENT_DIR/${BS}.json
  syncpods $BS
  let BS=2*BS
done
cleanup
