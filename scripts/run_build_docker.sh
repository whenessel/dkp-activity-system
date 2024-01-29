#!/usr/bin/env bash
docker buildx build --builder multiplatform --platform linux/arm64,linux/amd64 -f compose/Dockerfile -t whenessel/dkp-activity-system:local . --push
docker buildx build -f compose/Dockerfile -t whenessel/dkp-activity-system:local . --load


# PUSH TO HUB
# docker buildx build --builder multiplatform --platform linux/amd64,linux/arm64 -f compose/Dockerfile -t whenessel/dkp-activity-system:development . --push
# docker buildx imagetools create --tag whenessel/dkp-activity-system:2024.1.27 whenessel/dkp-activity-system:development
# docker buildx imagetools create --tag whenessel/dkp-activity-system:latest whenessel/dkp-activity-system:2024.1.27
# docker buildx imagetools create --tag whenessel/dkp-activity-system:latest whenessel/dkp-activity-system:development
