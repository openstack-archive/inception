#!/bin/bash
# install configure knife on the chef server

mkdir -p ~/.chef
sudo cp /etc/chef/validation.pem /etc/chef/webui.pem ~/.chef
sudo chown -R $USER ~/.chef

knife configure -i -r ~/chef-repo --admin-client-key ~/.chef/webui.pem --validation-key ~/.chef/validation.pem --defaults

