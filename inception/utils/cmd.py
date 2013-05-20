"""Command execution utils
"""

import subprocess


def local(cmd, screen_output=False):
    """
    Execute a local command

    @param cmd: a str, e.g., 'uname -a'
    @param screen_output: whether output to screen or capture the output

    @return: (output, error)
      if screen_output is True, return ("", "")
    """
    print 'executing command=', cmd
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
    if silent:
        flags.append('-o StrictHostKeyChecking=no')
        flags.append('-o UserKnownHostsFile=/dev/null')
    if agent_forwarding:
        flags.append('-A')
    cmd = 'ssh -p %s %s %s %s' % (port, ' '.join(flags), uri, cmd)
    print 'executing command=', cmd
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
