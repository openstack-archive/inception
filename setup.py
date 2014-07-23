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
    data_files=[('bin', ['bin/configure_knife.sh',
                         'bin/delete_docker_instances.sh',
                         'bin/install_chefserver_deps.sh',
                         'bin/install_chefserver.sh',
                         'bin/install_libvirt.sh',
                         'bin/install_openvswitch.sh',
                         'bin/install_zookeeper.sh',
                         'bin/launch_docker_instance.py',
                         'bin/launch_libvirt_instance.py',
                         'bin/setup_chef_repo.sh',
                         'bin/switch_kernel.sh',
                         'bin/userdata.sh.template',
                         ]),
                ('inception/webui/templates/inception',
                 ['inception/webui/templates/inception/detail.html',
                 'inception/webui/templates/inception/_detail_log.html',
                 'inception/webui/templates/inception/_detail_overview.html',
                 'inception/webui/templates/inception/_flavors_and_quotas.html',
                 'inception/webui/templates/inception/index.html',
                 'inception/webui/templates/inception/_launch_customize_help.html',
                 'inception/webui/templates/inception/_launch_details_help.html',
                 'inception/webui/templates/inception/_launch_network_help.html',
                 'inception/webui/templates/inception/_launch_volumes_help.html',
                 'inception/webui/templates/inception/_update_networks.html',
                 ]),
               ],
    scripts=['bin/orchestrator'],
)
