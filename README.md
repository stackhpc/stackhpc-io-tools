# To build the image:

    sudo docker build . -t brtknr/fio:v3.11.8 && sudo docker push brtknr/fio:v3.11.8

# To start and clean-up fio job on k8s:

    kubectl apply -f k8s/
    kubectl delete -f k8s/

# To generate plot:

    ./fio_parse.py --input-dir input/fio-2018-10-29-12:03:31/read-random --output-dir output/read-random --force

