#!/bin/bash

## Run this script after the start of the docker.
## Are there any other ways to run startup commands in the docker when container boots?

# Mount /etc/fstab
mount -a

# Start Netdata monitoring
/usr/sbin/netdata