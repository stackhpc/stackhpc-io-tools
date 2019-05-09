for c in 8; do
  for rw in write randwrite read randread; do
    make remote SCENARIO=beegfs FIO_RW=$rw NUM_CLIENTS=$c \
      DATA_PATH=/mnt/storage-nvme \
      RESULTS_PATH=/mnt/storage-nvme/bharat/results/bare \
      NUM_NODES=2 NODE_PREFIX=centos@kata-worker
  done
done
