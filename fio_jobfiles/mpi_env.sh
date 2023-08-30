#!/bin/bash

export SCENARIO=weka-vflag
export NNODES=16
export NPROCS=1
export FIO_RW=write
export FIO_NUM_JOBS=6
export DATA_PATH=/mnt/centos/fio-data
export RESULTS_PATH=/cluster/centos/fio-results

export BS_MIN=1024
export BS_MAX=$((2 * 1024 * 1024))
