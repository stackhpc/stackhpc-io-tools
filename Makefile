.EXPORT_ALL_VARIABLES:

# Tunable parameters - ALL CASES
SCENARIO ?= ceph
FIO_RW ?= randread
NUM_CLIENTS ?= 1

# Tunable parameters - if using Kubernetes
DATA_HOSTPATH ?= /mnt/ceph/bharat
RESULTS_HOSTPATH ?= /mnt/ceph/bharat/results

# Changing the options below is not recommended
DATA_PATH ?= data
RESULTS_PATH ?= results
FIO_JOBFILES ?= fio_jobfiles
DOCKER_ID ?= stackhpc
FIO_VERSION ?= 3.1
FIO_NUM_JOBS ?= 4

# DO NOT CHANGE
FIO_TAG = v${FIO_VERSION}
SCENARIO_NAME ?= ${SCENARIO}-${FIO_RW}
JOB_NAME ?= ${SCENARIO_NAME}-${NUM_CLIENTS}

all: docker k8s

docker: build push

k8s: delete create list

build: 
	sudo docker build . --build-arg FIO_VERSION=${FIO_VERSION} --build-arg FIO_JOBFILES=${FIO_JOBFILES} -t ${DOCKER_ID}/fio:${FIO_TAG}

push:
	sudo docker push ${DOCKER_ID}/fio:${FIO_TAG}

delete:
	-templater k8s/template.yml | kubectl delete -f -

create:
	templater k8s/template.yml | kubectl create -f -

follow:
	kubectl logs -f jobs/${JOB_NAME}

list:
	kubectl get pods -l job-name=${JOB_NAME}

process:
	fio_parse -o ${OUT} -i ${IN} -m ${MODE} -L -S 128 256

run:
	bash fio_jobfiles/run_fio.sh
