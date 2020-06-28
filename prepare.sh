#!/bin/bash

cur_dir=$(pwd)
sudo pip3 install virtualenv
sudo virtualenv -p /usr/bin/python3 $cur_dir
cd $cur_dir
echo -e "\nrun: source bin/activate\ncheck install.sh\n"

