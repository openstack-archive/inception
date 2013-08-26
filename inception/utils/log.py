# -*- coding: utf-8 -*-

# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Copyright (C) 2013 AT&T Labs Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""logging handler, it allows setting of formatting information through conf
"""

import logging
import os

from oslo.config import cfg

log_opts = [
    cfg.StrOpt('log_formatter',
               default=logging.Formatter('%(asctime)s - %(name)s - '
                                         '%(levelname)s - %(threadName)s - '
                                         '%(message)s'),
               help='log formatter'),
    cfg.StrOpt('log_dir',
               default=None,
               help='path of log file'),
    cfg.StrOpt('log_file',
               default=None,
               help='name of log file'),
    cfg.StrOpt('log_level',
               default='info',
               help='default logging level'),
]

CONF = cfg.CONF
CONF.register_cli_opts(log_opts)

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


def setup(product_name):
    """setup logger and its handlers"""
    LOGGER = logging.getLogger(product_name)
    log_level = LOG_LEVELS[CONF.log_level]
    LOGGER.setLevel(log_level)
    ## console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(CONF.log_formatter)
    LOGGER.addHandler(console_handler)
    ## file logging
    if CONF.log_dir is not None and CONF.log_file is not None:
        if not os.path.exists(CONF.log_dir):
            os.makedirs(CONF.log_dir)
        file_handler = logging.FileHandler(os.path.join(CONF.log_dir,
                                                        CONF.log_file))
        file_handler.setLevel(log_level)
        file_handler.setFormatter(CONF.log_formatter)
        LOGGER.addHandler(file_handler)
