# To build and push docker image

    make docker

# To deploy k8s job

    make k8s SPEC=k8s/beegfs-read.yaml

# To generate plot:

    ./fio_parse.py --input-dir input/fio-2018-10-29-12:03:31/read-random --output-dir output/read-random --force
