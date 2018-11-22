FROM centos:latest

ARG FIO_VERSION

ARG FIO_JOBFILES

RUN yum install -y fio-$FIO_VERSION

ADD fio_jobfiles $FIO_JOBFILES
