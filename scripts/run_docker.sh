#!/usr/bin/env bash
docker run --env-file ./.env -v ./src:/app/src --rm -it whenessel/dkp-activity-system:local runbot
