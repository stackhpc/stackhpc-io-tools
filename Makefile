FIO_VERSION ?= 3.1
FIO_TAG = v${FIO_VERSION}
DOCKER_ID ?= stackhpc

all: docker k8s

docker: build push

k8s: spec delete tag apply

build: 
	sudo docker build . --build-arg FIO_VERSION=${FIO_VERSION}  -t ${DOCKER_ID}/fio:${FIO_TAG}

push:
	sudo docker push ${DOCKER_ID}/fio:${FIO_TAG}

spec:
	if [ "" = "${SPEC}" ]; then echo "SPEC must be defined. For example, $$ make SPEC=k8s/beefs-read.yaml"; exit 1; fi

delete:
	-kubectl delete -f ${SPEC}

tag:
	sed -i 's/fio:v.*$$/fio:${FIO_TAG}/g' ${SPEC}

apply:
	kubectl apply -f ${SPEC}

process:
	fio_parse -o ${OUT} -i ${IN} -m ${MODE} -L -S 128 256
