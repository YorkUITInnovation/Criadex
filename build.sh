#!/bin/bash

docker buildx use retard-uit

docker buildx build --push \
--platform linux/amd64,linux/arm64 \
--tag uitadmin/criadex:latest \
--tag uitadmin/criadex:v1.7.7 .