#!/bin/bash

sudo apt update -qq
sudo apt install gettext -yq
pip3 install -r requirements/requirements-base.txt
pip3 install -r requirements/requirements-mysql.txt
./manage.py migrate
./manage.py compilemessages
./manage.py collectstatic -c --noinput
#./manage.py demosetup

