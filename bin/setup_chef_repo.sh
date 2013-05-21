#!/bin/bash
# setup chef repo
set -o nounset
set -e

HOSTNAME_ARRAY=(${HOSTNAME//-/ }) # split the hostname by "-"
PREFIX=${HOSTNAME_ARRAY[0]} # the first half is prefix
CHEF_REPO=${1}
CHEF_REPO_BRANCH=${2}

mkdir -p ~/chef-repo

# first, clone the repo
git clone -b ${CHEF_REPO_BRANCH} --recursive ${CHEF_REPO} ~/chef-repo

cd ~/chef-repo/environments/
./instantiate.sh ${PREFIX} allinone

cd ~/chef-repo
knife cookbook upload -a
knife environment from file environments/*.json
knife role from file roles/*.json
