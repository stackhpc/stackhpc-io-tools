for c in ${CLIENTS:-"1 8 64"}; do
  for rw in ${MODES:-"write randwrite read randread"}; do
    make k8s SCENARIO=beegfs FIO_RW=${rw} NUM_CLIENTS=${c} \
      DATA_HOSTPATH=/mnt/storage-nvme/bharat \
      RESULTS_HOSTPATH=/mnt/storage-ssd/bharat/results/runc
  done
done
