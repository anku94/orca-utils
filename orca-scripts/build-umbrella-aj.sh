#!/usr/bin/env bash

set -eu

export MPI_HOME=/users/ankushj/amr-workspace/mvapich-or-install-ub22
export PATH=$PATH:$MPI_HOME/bin

export CLONE_PREFIX=/l0/orcaroot/orcahax/oumb-tmp2
export BUILD_PREFIX=$CLONE_PREFIX/build
export INSTALL_PREFIX=$CLONE_PREFIX/install

exec "$(dirname "$0")/build-umbrella.sh"
