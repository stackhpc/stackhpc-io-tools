#! /bin/env bash

export FIO_VERSION=3.11

docker build . --build-arg FIO_VERSION=${FIO_VERSION} \
    -t brtknr/fio:v${FIO_VERSION} && \
    docker push brtknr/fio:v${FIO_VERSION}
