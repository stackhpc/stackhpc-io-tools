# To install

Installation from local files into a local virtualenv:

    virtualenv venv
    source venv/bin/activate
    pip install .

Installation direct from the git repo:

    pip install git+https://github.com/stackhpc/stackhpc-io-tools

# To build and push docker image

    make docker DOCKER_ID=stackhpc

# To run fio locally (which launches a single client locally)

    make local SCENARIO=beegfs FIO_RW=randread NUM_CLIENTS=1 \
    DATA_DIR=/path-to-test-dir RESULT_DIR=/path-to-result-dir

# Alternatively, to deploy multiple clients by creating k8s job

    make k8s SCENARIO=beegfs FIO_RW=randread NUM_CLIENTS=16 \
    DATA_HOSTPATH=/path-to-test-host-path RESULT_HOSTPATH=/path-to-result-host-path \
    DATA_DIR=/path-to-test-dir RESULT_DIR=/path-to-result-dir

# To generate plot:

    make parse RESULT_DIR=/path-to-result-dir OUTPUT_DIR=/path-to-output-dir

# Typical output figures:

![Blocksize vs commit latency](example-output/blocksize-vs-commit-latency.png)
![Commit latency frequency distribution](example-output/commit-latency-freq-dist.png)
![Stacked blocksize vs read bandwidth](example-output/stacked-blocksize-vs-bandwidth.png)
