#!/usr/bin/python
# Copyright (c) 2012 AT&T. All right reserved.
#

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


# move version string out of setup so it is readily available to others
from inception import __version__

setup(
    name='inception',
    version=__version__,
    description="Inception: Towards a Nested Cloud Architecture",
    license="Apache 2.0",
    classifiers=["Programming Language :: Python"],
    url='https://github.com/maoy/inception',
    packages=["inception"],
    install_requires=[
        "oslo.config>=1.1.1",
        "python-novaclient>=2.13.0",
        "IPython>=0.13.2",
    ],
)
