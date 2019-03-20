.EXPORT_ALL_VARIABLES:

# Configurable parameters - ALL CASES
SCENARIO ?= beegfs
FIO_RW ?= randread
NUM_CLIENTS ?= 1
DATA_PATH ?= data
RESULTS_PATH ?= results
OUTPUT_PATH ?= output
SKIP_BS ?= -1 

# Additional configurable parameters if using k8s
DATA_HOSTPATH ?= /mnt/storage-nvme/bharat
# DATA_HOSTPATH ?= /mnt/ceph/bharat
RESULTS_HOSTPATH ?= /mnt/storage-nvme/bharat/results
# RESULTS_HOSTPATH ?= /mnt/ceph/bharat/results

# Changing the options below is not recommended
FIO_JOBFILES ?= fio_jobfiles
DOCKER_ID ?= stackhpc
FIO_VERSION ?= 3.1
FIO_NUM_JOBS ?= 4

# DO NOT CHANGE
FIO_TAG = v${FIO_VERSION}
SCENARIO_NAME = ${SCENARIO}-${FIO_RW}
K8S_JOB_NAME = ${SCENARIO_NAME}-${NUM_CLIENTS}
IN = ${RESULTS_PATH}/${SCENARIO_NAME}
OUT = ${OUTPUT_PATH}/${SCENARIO_NAME}
ifeq (write, $(findstring write, ${FIO_RW}))
	MODE = write
else
	MODE = read
endif

all: docker local

docker: build push

k8s: create list wait delete

build: 
	sudo docker build . --build-arg FIO_VERSION=${FIO_VERSION} --build-arg FIO_JOBFILES=${FIO_JOBFILES} -t ${DOCKER_ID}/fio:${FIO_TAG}

push:
	sudo docker push ${DOCKER_ID}/fio:${FIO_TAG}

delete:
	-templater k8s/template.yml | kubectl delete -f -

create:
	-templater k8s/template.yml | kubectl create -f -

follow:
	kubectl logs -f jobs/${K8S_JOB_NAME}

list:
	kubectl get pods -l job-name=${K8S_JOB_NAME}

wait:
	kubectl wait --for=condition=complete jobs/${K8S_JOB_NAME} --timeout=-1s

parse:
	fio_parse -i ${IN}/${NUM_CLIENTS}/* -o ${OUT}/${NUM_CLIENTS} -S ${SKIP_BS} -m ${FIO_RW} -s ${SCENARIO} ${ARGS} -L -f

local:
	bash fio_jobfiles/run_fio.sh

test:
	unit2
