#!/usr/bin/python
# Copyright (c) 2012 AT&T. All right reserved.
#

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '0.0.1'

setup(
    name='inception',
    version=version,
    description="Inception: Towards a Nested Cloud Architecture",
    license="Apache 2.0",
    classifiers=["Programming Language :: Python"],
    url='https://github.com/maoy/inception',
    packages=["inception"],
    install_requires=[
        "python-novaclient>=2.13.0",
        "IPython>=0.13.2",
    ],
)
