#!/bin/bash

source mpi_env.sh

for ((n=1; $n <= $NNODES; n=$n+1))
do
    for ((i=$BS_MIN; $i <= $BS_MAX; i=$i * 2))
    do
	echo Nodes: $n Procs: $NPROCS Blocksize: $i 
	mpirun -N $NPROCS --np $(($n * $NPROCS)) --hostfile ~/mpi_hosts --tag-output mpi_fio.sh $i
    done
done
