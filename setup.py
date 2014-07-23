#!/usr/bin/env python
# Copyright (c) 2013 AT&T. All right reserved.

from setuptools import find_packages
from setuptools import setup

# move version string out of setup so it is readily available to others
from inception import __version__

setup(
    name='inception',
    version=__version__,
    description="Inception: Towards a Nested Cloud Architecture",
    license="Apache 2.0",
    classifiers=["Programming Language :: Python"],
    url='https://github.com/stackforge/inception',
    packages=find_packages(),
    install_requires=[
        "oslo.config>=1.1.1",
        "python-novaclient>=2.13.0",
        "IPython>=0.13.2",
    ],
    data_files=[
        ('bin', [
            # 'configure_knife.sh',
            # 'delete_docker_instances.sh',
            # 'install_chefserver_deps.sh',
            # 'install_chefserver.sh',
            # 'install_libvirt.sh',
            # 'install_openvswitch.sh',
            # 'install_zookeeper.sh',
            # 'launch_docker_instance.py',
            # 'launch_libvirt_instance.py',
            # 'setup_chef_repo.sh',
            # 'switch_kernel.sh',
            # 'userdata.sh.template',
        ]),
        ('inception/webui/templates/inception', [
            # 'detail.html',
            # '_detail_log.html',
            # '_detail_overview.html',
            # '_flavors_and_quotas.html',
            # 'index.html',
            # '_launch_customize_help.html',
            # '_launch_details_help.html',
            # '_launch_network_help.html',
            # '_launch_volumes_help.html',
            # '_update_networks.html',
        ]),
    ],
    scripts=['bin/orchestrator'],
)
