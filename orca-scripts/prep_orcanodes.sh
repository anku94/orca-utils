#!/usr/bin/env bash

set -eu

QIB_KO=/users/ankushj/downloads/ib_qib.ko
LUSTRE_SH=/users/ankushj/scripts/lustre-mount.sh

node_message() {
    local node_name=$(hostname)
    echo "-INFO- [$node_name] $@"
}

node_message "Prepping node: $(hostname)"

if mountpoint -q /mnt/ltio; then
    node_message "Unmounting lustre"
    sudo umount /mnt/ltio
fi

node_message "Unloading lustre kernel modules..."
sudo lustre_rmmod

node_message "Unloading ib_qib module..."
sudo modprobe -r ib_qib

# if /ipathfs exists, unmount it
if mountpoint -q /ipathfs; then
    node_message "Unmounting /ipathfs"
    sudo umount /ipathfs
fi

node_message "Setting up tuned qib config..."
sudo modprobe rdmavt
sudo insmod $QIB_KO sdma_fetch_prio=15 cfgctxts=6 krcvqs=5 sdma_descq_cnt=512

sleep 1

node_message "Mounting lustre..."
NOCONFIG=0 $LUSTRE_SH 10.94.3.109 /mnt/ltio
