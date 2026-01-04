#!/bin/bash

docker buildx build --push \
--platform linux/amd64,linux/arm64 \
--tag uitadmin/criadex:latest-beta \
--tag uitadmin/criadex:v1.8.1-beta .