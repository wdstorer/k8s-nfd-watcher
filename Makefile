NAME=nfd-watcher
VERSION=0.1.30
IMAGE_NAME=wdstorer/$(NAME):$(VERSION)

build-image:
	docker build -t $(IMAGE_NAME) .

build-image-no-cache:
	docker build --no-cache -t $(IMAGE_NAME) .

push-image:
	docker push $(IMAGE_NAME)

push: build-image push-image

