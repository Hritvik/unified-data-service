SHELL := /bin/bash

IMAGE_REGISTRY ?= ghcr.io
IMAGE_NAMESPACE ?= local
IMAGE_NAME ?= unified-data-service
IMAGE_TAG ?= dev
IMAGE := $(IMAGE_REGISTRY)/$(IMAGE_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)

LOCAL_COMPOSE := docker-compose.local.yml
REGISTRY_COMPOSE := docker-compose.registry.yml

.PHONY: up down restart status logs health image-build image-push image-pull registry-up registry-down registry-restart registry-logs registry-health

up:
	docker compose -f $(LOCAL_COMPOSE) up --build -d

down:
	docker compose -f $(LOCAL_COMPOSE) down

restart: down up

status:
	docker compose -f $(LOCAL_COMPOSE) ps

logs:
	docker compose -f $(LOCAL_COMPOSE) logs -f unified-data-service

health:
	curl -fsS http://localhost:8080/health

image-build:
	docker build -t $(IMAGE) .

image-push: image-build
	docker push $(IMAGE)

image-pull:
	docker pull $(IMAGE)

registry-up:
	UDS_IMAGE=$(IMAGE) docker compose -f $(REGISTRY_COMPOSE) up -d

registry-down:
	docker compose -f $(REGISTRY_COMPOSE) down

registry-restart: registry-down registry-up

registry-logs:
	docker compose -f $(REGISTRY_COMPOSE) logs -f unified-data-service

registry-health:
	curl -fsS http://localhost:8080/health
