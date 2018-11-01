#! /bin/env bash

export FIO_VERSION=3.11
export FIO_TAG=v${FIO_VERSION}.10

sudo docker build . --build-arg FIO_VERSION=${FIO_VERSION} \
    -t brtknr/fio:${FIO_TAG} && \
    sudo docker push brtknr/fio:${FIO_TAG} && \
    sed -i 's/fio:v.*$/fio:'${FIO_TAG}'/g' k8s/jobs.yaml
kubectl delete -f k8s/jobs.yaml
kubectl apply -f k8s/jobs.yaml
