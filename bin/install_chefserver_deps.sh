#!/bin/bash

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

sudo apt-get install -y libgnumail-java ruby-addressable libextlib-ruby jsvc \
  libdb5.1-java-gcj erlang-eunit libjaxp1.3-java libcommons-pool-java \
  libdb-je-java ruby-mixlib-config gcj-4.6-jre-lib libjson-ruby1.8 \
  libbcel-java erlang-crypto libgeronimo-jta-1.1-spec-java libecj-java \
  libmixlib-authentication-ruby1.8 libopenid-ruby libmerb-helpers-ruby \
  gcj-4.6-base erlang-corba libxerces2-java libportlet-api-2.0-spec-java \
  libeventmachine-ruby erlang-asn1 libnss3 libgcj-bc erlang-xmerl libicu48 \
  libcommons-fileupload-java libjtidy-java ohai ruby-daemons ruby-mime-types \
  erlang-snmp libicu4j-java erlang-tools libtreetop-ruby \
  libcommons-beanutils-java libdep-selector-ruby erlang-edoc libgecodegist30 \
  ruby-net-ssh-multi libmixlib-log-ruby1.8 ruby-json unzip libgnuinet-java \
  ruby-mixlib-shellout erlang-syntax-tools ruby-systemu rubygems libdb-java \
  libsctp1 libgecode-dev libpolyglot-ruby rake libgecode30 libgecode27 \
  ruby-net-ssh-gateway libmoneta-ruby java-common lksctp-tools \
  libaddressable-ruby icedtea-6-jre-cacao default-jre-headless libmozjs185-1.0 \
  libcommons-logging-java jetty libcommons-compress-java ruby-net-ssh \
  openjdk-6-jre-lib erlang-webtool libmerb-haml-ruby ruby-ipaddress \
  erlang-diameter apache2-utils libgcj12 libmerb-core-ruby1.8 libdb5.1-java \
  couchdb-bin erlang-runtime-tools libbunny-ruby openjdk-6-jre-headless \
  ruby-rack thin erlang-docbuilder ruby-uuidtools ant solr-jetty \
  libgnujaf-java solr-common librestclient-ruby ruby-eventmachine \
  libxml-commons-resolver1.1-java merb-core libamqp-ruby libboost1.46-dev \
  ant-optional libtomcat6-java libfast-xs-ruby ruby-sass libjetty-extra \
  erlang-inviso libapache-pom-java icedtea-6-jre-jamvm libsystemu-ruby1.8 \
  libmx4j-java libjson-ruby libescape-utils-ruby libxml-commons-external-java \
  libhmac-ruby1.8 libmixlib-config-ruby rabbitmq-server tzdata-java \
  libohai-ruby libcommons-dbcp-java erlang-mnesia erlang-public-key erlang-dev \
  libxml-ruby1.8 libmixlib-authentication-ruby libmerb-helpers-ruby1.8 \
  librack-ruby libnet-ssh-multi-ruby libservlet2.5-java \
  libcommons-httpclient-java erlang-os-mon libnspr4 libmerb-assets-ruby1.8 \
  ruby-libxml glassfish-mail libmerb-param-protection-ruby1.8 libcoderay-ruby \
  libmixlib-log-ruby libem-http-request-ruby libmerb-haml-ruby1.8 \
  libslf4j-java erlang-erl-docgen libcommons-daemon-java libuuidtools-ruby \
  erlang-inets libnet-ssh2-ruby erlang-ic ruby-highline libregexp-java \
  libgecodeflatzinc30 erlang-odbc zip erlang-nox ruby-erubis libhighline-ruby \
  ruby-coderay libbunny-ruby1.8 libmerb-assets-ruby libcommons-codec-java \
  ca-certificates-java libhaml-ruby1.8 couchdb erlang-ssh erlang-percept \
  liblucene2-java erlang-ssl libmixlib-cli-ruby libcommons-parent-java \
  libcommons-collections3-java libboost-dev libgcj-common ruby-haml libodbc1 \
  libmixlib-cli-ruby1.8 libcommons-csv-java libyajl-ruby \
  libcommons-digester-java libmoneta-ruby1.8 libjetty-java erlang-parsetools \
  liblog4j1.2-java libjline-java libcommons-io-java libnss3-1d libohai-ruby1.8 \
  libmerb-param-protection-ruby ruby-rest-client ruby-hmac libextlib-ruby1.8 \
  erlang-base liberubis-ruby libopenid-ruby1.8 libjetty-extra-java
