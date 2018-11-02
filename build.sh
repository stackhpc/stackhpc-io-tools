#! /bin/env bash

export FIO_VERSION=3.11
export FIO_TAG=v${FIO_VERSION}.11
export K8S_JOBSPEC=k8s/beegfs-jobs.yml

sudo docker build . --build-arg FIO_VERSION=${FIO_VERSION} \
    -t brtknr/fio:${FIO_TAG} && \
    sudo docker push brtknr/fio:${FIO_TAG} && \
    sed -i 's/fio:v.*$/fio:'${FIO_TAG}'/g' ${K8S_JOBSPEC}
kubectl delete -f ${K8S_JOBSPEC}
kubectl apply -f ${K8S_JOBSPEC}
