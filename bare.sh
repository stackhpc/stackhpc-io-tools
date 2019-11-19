for c in ${CLIENTS:-"1 8 64"}; do
  for rw in ${MODES:-"write randwrite read randread"}; do
    make remote SCENARIO=beegfs FIO_RW=${rw} NUM_CLIENTS=${c} \
      DATA_PATH=/mnt/storage-nvme/bharat \
      RESULTS_PATH=/mnt/storage-ssd/bharat/results/bare \
      NUM_NODES=2 NODE_PREFIX=centos@kata-worker
  done
done
