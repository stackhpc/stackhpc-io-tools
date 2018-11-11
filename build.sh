#! /bin/env bash

export FIO_VERSION=3.1
export FIO_TAG=v${FIO_VERSION}
export K8S_JOBSPEC=k8s/ceph-randread.yaml

kubectl delete -f ${K8S_JOBSPEC}

sudo docker build . --build-arg FIO_VERSION=${FIO_VERSION} \
    -t brtknr/fio:${FIO_TAG} && \
    sudo docker push brtknr/fio:${FIO_TAG} && \
    sed -i 's/fio:v.*$/fio:'${FIO_TAG}'/g' ${K8S_JOBSPEC} && \
    kubectl apply -f ${K8S_JOBSPEC}
