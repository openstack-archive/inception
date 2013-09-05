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

"""Command execution utils
"""

import logging
import subprocess

LOGGER = logging.getLogger(__name__)


def local(cmd, screen_output=False):
    """
    Execute a local command

    @param cmd: a str, e.g., 'uname -a'
    @param screen_output: whether output to screen or capture the output

    @return: (output, error)
      if screen_output is True, return ("", "")
    """
    LOGGER.info('executing command=%s', cmd)
    stdout, stderr = ((None, None) if screen_output
                      else (subprocess.PIPE, subprocess.PIPE))
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=None,
                            stderr=stderr,
                            stdout=stdout)
    out, error = proc.communicate()  # 0: stdout, 1:stderr
    if proc.returncode > 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=out)
    if screen_output:
        return ("", "")
    else:
        return out.rstrip('\n'), error  # remove trailing '\n'


class SshConnectionError(subprocess.CalledProcessError):
    """connection error in ssh"""
    pass


def ssh(uri, cmd, screen_output=False, silent=True, agent_forwarding=False):
    """
    Execute a remote command via ssh

    @param uri: <user>@<ipaddr/hostname>[:port]
    @param cmd: a str, e.g., 'uname -a'
    @param screen_output: whether output to screen or capture the output
    @param silent: whether prompt for yes/no questions

    @return: (output, error)
      if screen_output is True, return ("", "")
    """
    ## if ssh port forwarding address, find out the port
    if ':' in uri:
        uri, port = uri.split(':')
    ## default port
    else:
        port = 22
    ## construct flags
    flags = ['-T']
    flags.append('-n')   # prevent read blocking on tty (stdin)
    if silent:
        flags.append('-o StrictHostKeyChecking=no')
        flags.append('-o UserKnownHostsFile=/dev/null')
    if agent_forwarding:
        flags.append('-A')
    cmd = 'ssh -p %s %s %s %s' % (port, ' '.join(flags), uri, cmd)
    LOGGER.info('executing command=%s', cmd)
    stdout, stderr = ((None, None) if screen_output
                      else (subprocess.PIPE, subprocess.PIPE))
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=None,
                            stderr=stderr,
                            stdout=stdout)
    out, error = proc.communicate()  # 0: stdout, 1:stderr
    ctor = (SshConnectionError if proc.returncode == 255
            else subprocess.CalledProcessError)
    if proc.returncode > 0:
        raise ctor(proc.returncode, cmd, output=out)
    if screen_output:
        return ("", "")
    else:
        return out.rstrip('\n'), error  # remove trailing '\n'
