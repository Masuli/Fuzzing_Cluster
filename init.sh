#!/bin/sh
docker build . -t raspberry
chmod 666 /var/run/docker.sock
