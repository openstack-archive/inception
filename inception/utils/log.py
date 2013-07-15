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
