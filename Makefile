.EXPORT_ALL_VARIABLES:

# Configurable parameters - ALL CASES
SCENARIO ?= beegfs
FIO_RW ?= randread
NUM_CLIENTS ?= 1
DATA_PATH ?= data
RESULTS_PATH ?= results
OUTPUT_PATH ?= output
SKIP_BS ?= -1 
NUM_NODES ?= 1
RUNTIME_CLASS ?= #kata-qemu
NUM_CLIENTS_PER_NODE:= $(shell echo ${NUM_CLIENTS} / ${NUM_NODES} | bc)
MAX_NODE_INDEX := $(shell echo ${NUM_NODES} - 1 | bc)
MAX_CLIENT_INDEX:= $(shell echo ${NUM_CLIENTS} - 1 | bc)

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
FIO_TAG = v${FIO_VERSION}.3

# DO NOT CHANGE
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

k8s: delete create list wait

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
	kubectl get pods -l job-name=${K8S_JOB_NAME} -o wide

wait:
	kubectl wait --for=condition=complete jobs/${K8S_JOB_NAME} --timeout=-1s

parse:
	fio_blocksize -i ${IN} -o ${OUT}/${NUM_CLIENTS} -S ${SKIP_BS} -m ${FIO_RW} -s ${SCENARIO} ${ARGS} -L -f -c ${NUM_CLIENTS}
	#fio_client -i ${IN}/${NUM_CLIENTS}/* -o ${OUT}/${NUM_CLIENTS} -S ${SKIP_BS} -m ${FIO_RW} -s ${SCENARIO} ${ARGS} -L -f

copy:
	for i in {0..${MAX_NODE_INDEX}}; do\
		scp -r fio_jobfiles/ ${NODE_PREFIX}-$$i:;\
	done

remote:
	for i in {0..${MAX_CLIENT_INDEX}}; do \
		ssh ${NODE_PREFIX}-$$(( $$i % ${NUM_NODES} )) NUM_NODES=${NUM_NODES} FIO_RW=${FIO_RW} FIO_NUM_JOBS=${FIO_NUM_JOBS} FIO_JOBFILES=${FIO_JOBFILES} DATA_PATH=${DATA_PATH} RESULTS_PATH=${RESULTS_PATH} NUM_CLIENTS=${NUM_CLIENTS} SCENARIO_NAME=${SCENARIO_NAME} CLIENT_NAME=${K8S_JOB_NAME}-client-$$$$-$$i sudo -E bash fio_jobfiles/run_fio.sh & \
	done; sleep 10; wait

local:
	bash fio_jobfiles/run_fio.sh

test:
	unit2
