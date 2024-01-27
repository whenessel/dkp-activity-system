#!/usr/bin/env bash
docker buildx build --builder multiplatform --platform linux/arm64,linux/amd64 -f compose/Dockerfile -t whenessel/dkp-activity-system:local . --push
docker buildx build -f compose/Dockerfile -t whenessel/dkp-activity-system:local . --load
