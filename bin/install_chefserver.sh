#!/bin/bash
# install chef server from opscode repo via apt

CHEF_SERVER=$(hostname -i)
CHEF_PASSWORD=${CHEF_PASSWORD:-ChefServer}

echo "deb http://apt.opscode.com/ `lsb_release -cs`-0.10 main" | \
	sudo tee /etc/apt/sources.list.d/opscode.list

sudo mkdir -p /etc/apt/trusted.gpg.d
gpg --keyserver keys.gnupg.net --recv-keys 83EF826A
gpg --export packages@opscode.com | \
	sudo tee /etc/apt/trusted.gpg.d/opscode-keyring.gpg > /dev/null

sudo apt-get update

sudo apt-get install -y opscode-keyring # permanent upgradeable keyring
sudo apt-get install -y debconf-utils
sudo apt-get -y upgrade

cat > /tmp/chef_seed << EOF
# New password for the 'admin' user in the Chef Server WebUI:
chef-server-webui chef-server-webui/admin_password password ${CHEF_PASSWORD}
# New password for the 'chef' AMQP user in the RabbitMQ vhost "/chef":
chef-solr chef-solr/amqp_password password ${CHEF_PASSWORD}
# URL of Chef Server (e.g., http://chef.example.com:4000):
chef chef/chef_server_url string http://${CHEF_SERVER}:4000
EOF

sudo debconf-set-selections < /tmp/chef_seed
rm -rf /tmp/chef_seed

sudo apt-get -y install chef chef-server chef-server-api chef-expander
