for c in 1 8 64; do
  for rw in write randwrite read randread; do
    make k8s SCENARIO=beegfs FIO_RW=$rw NUM_CLIENTS=$c \
      DATA_HOSTPATH=/mnt/storage-nvme \
      RESULTS_HOSTPATH=/mnt/storage-nvme/bharat/results/kata-nemu \
      RUNTIME_CLASS=kata-nemu
  done
done
