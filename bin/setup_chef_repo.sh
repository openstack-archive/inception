#!/bin/bash
# setup chef repo
set -o nounset
set -e

HOSTNAME_ARRAY=(${HOSTNAME//-/ }) # split the hostname by "-"
PREFIX=${HOSTNAME_ARRAY[0]} # the first half is prefix
mkdir -p ~/chef-repo

# first, clone the repo
git clone --recursive git://github.com/maoy/inception-chef-repo.git ~/chef-repo

cd ~/chef-repo/environments/
./instantiate.sh ${PREFIX} allinone

cd ~/chef-repo
knife cookbook upload -a
knife environment from file environments/*.json
knife role from file roles/*.json

