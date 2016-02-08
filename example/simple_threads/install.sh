#!/bin/bash

pushd `dirname $0` > /dev/null
PRJPATH=`pwd`
popd > /dev/null
FIXTURESPATH=${PRJPATH}/fixtures

#------------------------------
#printf "Checking Django version... "
#django_version=`python -c 'import django; print(django.get_version())'`
#printf "${django_version}\n"

python manage.py migrate --noinput

#------------------------------
#printf "Checking django_comments_xtd parent app... "
#django_comments=`python -c 'import imp
#try:
#    imp.find_module("django_comments")
#    print("django_comments")
#except ImportError:
#    print("django.contrib.comments")
#'`
#printf "${django_comments}\n"

fixtures=(auth sites articles django_comments django_comments_xtd)
for file in ${fixtures[@]}; do
    python manage.py loaddata ${FIXTURESPATH}/${file}.json
done
