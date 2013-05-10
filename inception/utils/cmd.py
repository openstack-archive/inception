"""Command execution utils
"""

import subprocess


def local(cmd):
    """
    Execute a local command

    @param cmd: a str, e.g., 'uname -a'
    """
    print 'executing command=', cmd
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=None,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    out, error = proc.communicate()  # 0: stdout, 1:stderr
    return out.rstrip('\n'), error  # remove trailing '\n'


def ssh(uri, cmd, silent=True, output_to_screen=False):
    """
    Execute a remote command via ssh

    @param uri: <user>@<ipaddr/hostname>[:port]
    @param cmd: a str, e.g., 'uname -a'
    @param silent: whether prompt for yes/no questions
    """
    ## if ssh port forwarding address, find out the port
    if ':' in uri:
        uri, port = uri.split(':')
    ## default port
    else:
        port = 22
    flag = ('-T -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
            if silent else '-T')
    cmd = 'ssh -p %s %s %s %s' % (port, flag, uri, cmd)
    print 'executing command=', cmd
    if output_to_screen:
        out = subprocess.check_call([e for e in cmd.split(' ') if e])
        return (out, None)
    else:
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdin=None,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        out, error = proc.communicate()  # 0: stdout, 1:stderr
        if any(s in error for s in ["No route to host",
                                    "Connection timed out",
                                    "Connection refused",
                                    "Connection closed by remote host"]):
            raise RuntimeError('host can not be reached via ssh')
        return out.rstrip('\n'), error  # remove trailing '\n'
