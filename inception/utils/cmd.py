"""Command execution utils
"""

import subprocess


def local(cmd, screen_output=False):
    """
    Execute a local command

    @param cmd: a str, e.g., 'uname -a'
    """
    print 'executing command=', cmd
    if screen_output:
        out = subprocess.check_call([e for e in cmd.split(' ') if e])
        return (str(out), "")
    else:
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdin=None,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        out, error = proc.communicate()  # 0: stdout, 1:stderr
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
      if screen_output is False, return ("", "")
    """
    ## if ssh port forwarding address, find out the port
    if ':' in uri:
        uri, port = uri.split(':')
    ## default port
    else:
        port = 22
    flag = '-T'
    if silent:
        flag += ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    if agent_forwarding:
        flag += ' -A'
    cmd = 'ssh -p %s %s %s %s' % (port, flag, uri, cmd)
    print 'executing command=', cmd
    if screen_output:
        stdout = None
        stderr = None
    else:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=None,
                            stderr=stderr,
                            stdout=stdout)
    out, error = proc.communicate()  # 0: stdout, 1:stderr
    ctor = subprocess.CalledProcessError
    if proc.returncode == 255:
        ctor = SshConnectionError
    if proc.returncode > 0:
        raise ctor(proc.returncode, cmd, output=out)
    if screen_output:
        return ("", "")
    return out.rstrip('\n'), error  # remove trailing '\n'
