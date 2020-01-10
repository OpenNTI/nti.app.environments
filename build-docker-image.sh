#!/bin/bash
if [ "$1" == "" ]; then
    echo "Specify an image name to give your container"
else
    ssh-add -K ~/.ssh/id_rsa
    export DOCKER_BUILDKIT=1
    docker build --ssh default . -t "$1"
fi