FROM centos:latest

ARG FIO_VERSION

RUN yum install -y fio-$FIO_VERSION

ADD fio_jobfiles /fio_jobfiles
