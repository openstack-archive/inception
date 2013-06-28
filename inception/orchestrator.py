#!/usr/bin/env python
"""
#TODO(changbl)
Networks:
(use /24 address for now (faster OpenStack deployment), increase to /16 later)

eth0, management: inherent interface on each rVM
eth1, ops: 10.251.x.x/16
eth2, private: 10.252.x.x/16
eth3, public: 172.31.x.x/16

rVMs eth1 IPs
[prefix]-gateway, 10.251.0.1
[prefix]-chefserver, 10.251.0.2
[prefix]-controller(s), 10.251.0.3 [ - 10.251.0.255] # maximum 253
[prefix]-worker-1, 10.251.1.1
[prefix]-worker-2(s), 10.251.1.2 [ - 10.251.255.254] # maximum ~65000

#TODO(to-be-assigned)
WebUI: Horizon-based

#TODO(to-be-assigned)
templatize all templatable configurations (environments, roles, etc), put the
rest (sensitive data) in a private configuration file specific to each
developer/user
"""

from collections import OrderedDict
import functools
import getopt
import os
import Queue
import subprocess
import sys
import threading
import time
import traceback

import IPython
from novaclient.v1_1.client import Client
from oslo.config import cfg

from inception.utils import cmd

CONF = cfg.CONF

cli_opts = [
    cfg.StrOpt('prefix',
               default=None,
               metavar='PREFIX',
               required=True,
               short='p',
               help='(unique) prefix for node names (no hyphens allowed)'),
    cfg.IntOpt('num_workers',
               default=2,
               metavar='NUM',
               short='n',
               help='number of worker nodes to create'),
    cfg.BoolOpt('shell',
                default=False,
                help='initialize, then drop to embedded IPython shell'),
    cfg.BoolOpt('atomic',
                default=False,
                help='on error, run as if --cleanup was specified'),
    cfg.BoolOpt('cleanup',
                default=False,
                help='take down the inception cloud'),
    cfg.BoolOpt('parallel',
                default=False,
                help='execute chef-related setup tasks in parallel'),
    cfg.StrOpt('chef_repo',
               default='git://github.com/maoy/inception-chef-repo.git',
               metavar='URL',
               help='URL of Chef repo'),
    cfg.StrOpt('chef_repo_branch',
               default='master',
               metavar='BRANCH',
               help='name of branch of Chef repo to use'),
    cfg.StrOpt('ssh_keyfile',
               default=None,
               metavar='PATH',
               help='path of additional keyfile for node access via ssh'),
    cfg.StrOpt('pool',
               default='research',
               help='name of pool for floating IP addresses'),
]

cfg_file_opts = [
    cfg.StrOpt('user',
               default='ubuntu',
               help=''),
    cfg.StrOpt('image',
               default='f3d62d5b-a76b-4997-a579-ff946a606132',
               help=''),
    cfg.IntOpt('flavor',
               default=3,
               help='id of machine flavor used for nodes'),
    cfg.IntOpt('gateway_flavor',
               default=1,
               help='id of machine flavor used for gateway'),
    cfg.StrOpt('key_name',
               default='af-keypair',
#               default='shared',
               help='name of key for node access via ssh'),
    cfg.ListOpt('security_groups',
                default=['default', 'ssh'],
                help='list of security groups for nodes'),
    cfg.StrOpt('src_dir',
               default='../bin/',
               help='path of setup script source dir on client'),
    cfg.StrOpt('dst_dir',
               default='/home/ubuntu/',
               help='path of setup script destination dir on nodes'),
    cfg.StrOpt('userdata',
               default='userdata.sh.template',
               help='template for user data script'),
    cfg.IntOpt('timeout',
               default=999999,
               help='number of seconds for creation timeout'),
    cfg.IntOpt('poll_interval',
               default=5,
               help='interval (in seconds) between readiness polls'),
]


class Orchestrator(object):
    """
    orchestrate all inception cloud stuff
    """

    def __init__(self, conf):
        """
        @param conf: instance of ConfigOpts() from oslo.config representing the
            totality of configuration values from the defaults in this source,
            the configuration file(s) (if any) and the command line
        """

        ## check config
        #TODO(changbl): remove the restriction of "num_workers <= 5"
        if conf.num_workers > 5:
            raise ValueError("currently only supports num_workers <= 5")
        #TODO(changbl): make separator '-' a constant and accessible
        #everywhere
        if '-' in conf.prefix:
            raise ValueError('"-" cannot exist in prefix=%r' % conf.prefix)

        # save configuration
        self.conf = conf

        # make src and dst dirs into absolute paths
        self.src_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                    conf.src_dir)
        self.dst_dir = os.path.abspath(conf.dst_dir)

        # get the userdata
        with open(os.path.join(self.src_dir, conf.userdata), 'r') as fin:
            self._userdata = fin.read()

        # Inject the extra ssh public key if any
        ssh_keycontent = ''
        if conf.ssh_keyfile:
            with open(conf.ssh_keyfile, 'r') as fin:
                ssh_keycontent = fin.read()
        self._userdata = self._userdata % (conf.user, ssh_keycontent)

        # scripts to run on chefserver, execute one by one (sequence matters)
        self.chefserver_commands = []
        self.chefserver_files = OrderedDict()

        for filename in ('install_chefserver.sh', 'configure_knife.sh',
                         'setup_chef_repo.sh'):
            src_file = os.path.join(self.src_dir, filename)
            dst_file = os.path.join(self.dst_dir, filename)
            if filename == 'setup_chef_repo.sh':
                # add two args to this command
                command = ("/bin/bash" + " " + dst_file + " " +
                           self.conf.chef_repo + " " +
                           self.conf.chef_repo_branch)
            else:
                command = "/bin/bash" + " " + dst_file
            self.chefserver_commands.append(command)
            with open(src_file, 'r') as fin:
                value = fin.read()
                key = dst_file
                self.chefserver_files[key] = value

        ## non-args
        self.client = Client(os.environ['OS_USERNAME'],
                             os.environ['OS_PASSWORD'],
                             os.environ['OS_TENANT_NAME'],
                             os.environ['OS_AUTH_URL'])
        self._gateway_id = None
        self._gateway_ip = None
        self._gateway_name = None
        self._chefserver_id = None
        self._chefserver_ip = None
        self._chefserver_name = None
        self._controller_id = None
        self._controller_ip = None
        self._controller_name = None
        self._worker_ids = []
        self._worker_ips = []
        self._worker_names = []
        self._gateway_floating_ip = None

    def start(self):
        """
        run the whole process
        """
        try:
            self._check_existence()
            self._create_servers()
            self._setup_chefserver()
            self._checkin_chefserver()
            self._deploy_network_vxlan()
            self._deploy_dnsmasq()
            self._setup_controller()
            self._setup_workers()
            print "Your inception cloud '%s' is ready!!!" % self.conf.prefix
            print "Gateway IP is %s" % self._gateway_floating_ip.ip
            print "Chef server WebUI is http://%s:4040" % self._chefserver_ip
            print "OpenStack dashboard is https://%s" % self._controller_ip
        except Exception:
            print traceback.format_exc()
            if self.conf.atomic:
                self.cleanup()

    def _check_existence(self):
        """
        Check whether inception cloud existence based on given self.prefix
        """
        prefix = self.conf.prefix + '-'
        for server in self.client.servers.list():
            if (server.name.startswith(prefix)):
                raise ValueError('prefix=%s is already used' %
                                 self.conf.prefix)

    def _create_servers(self):
        """
        start all VM servers: gateway, chefserver, controller, and workers, via
        calling Nova client API
        """
        # launch gateway
        gateway = self.client.servers.create(
            name=self.conf.prefix + '-gateway',
            image=self.conf.image,
            flavor=self.conf.gateway_flavor,
            key_name=self.conf.key_name,
            security_groups=self.conf.security_groups,
            userdata=self._userdata)
        self._gateway_id = gateway.id
        print "Creating %s" % gateway

        # launch chefserver
        chefserver = self.client.servers.create(
            name=self.conf.prefix + '-chefserver',
            image=self.conf.image,
            flavor=self.conf.flavor,
            key_name=self.conf.key_name,
            security_groups=self.conf.security_groups,
            userdata=self._userdata,
            files=self.chefserver_files)
        self._chefserver_id = chefserver.id
        print "Creating %s" % chefserver

        # launch controller
        controller = self.client.servers.create(
            name=self.conf.prefix + '-controller',
            image=self.conf.image,
            flavor=self.conf.flavor,
            key_name=self.conf.key_name,
            security_groups=self.conf.security_groups,
            userdata=self._userdata)
        self._controller_id = controller.id
        print "Creating %s" % controller

        # launch workers
        for i in xrange(self.conf.num_workers):
            worker = self.client.servers.create(
                name=self.conf.prefix + '-worker%s' % (i + 1),
                image=self.conf.image,
                flavor=self.conf.flavor,
                key_name=self.conf.key_name,
                security_groups=self.conf.security_groups,
                userdata=self._userdata)
            self._worker_ids.append(worker.id)
            print "Creating %s" % worker

        print ('wait at most %s seconds for servers to be ready (ssh-able + '
               'userdata done)' % self.conf.timeout)
        servers_ready = False
        begin_time = time.time()
        while time.time() - begin_time <= self.conf.timeout:
            try:
                # get IP addr of servers
                (self._gateway_ip, self._gateway_name) = self._get_server_info(
                    self._gateway_id)
                (self._chefserver_ip, self._chefserver_name) = (
                    self._get_server_info(self._chefserver_id))
                (self._controller_ip, self._controller_name) = (
                    self._get_server_info(self._controller_id))
                # clear content upon each time retry
                self._worker_ips = []
                self._worker_names = []
                for _id in self._worker_ids:
                    (ipaddr, name) = self._get_server_info(_id)
                    self._worker_ips.append(ipaddr)
                    self._worker_names.append(name)
                # test ssh-able
                command = '[ -d /etc/inception ]'
                cmd.ssh(self.conf.user + "@" + self._gateway_ip, command)
                cmd.ssh(self.conf.user + "@" + self._chefserver_ip, command)
                cmd.ssh(self.conf.user + "@" + self._controller_ip, command)
                for worker_ip in self._worker_ips:
                    cmd.ssh(self.conf.user + "@" + worker_ip, command)
                # indicate that servers are ready
                servers_ready = True
                break
            except (UnboundLocalError, subprocess.CalledProcessError) as error:
                print ('servers are not all ready, error=%s, sleep %s seconds'
                       % (error, self.conf.poll_interval))
                time.sleep(self.conf.poll_interval)
                continue
        if not servers_ready:
            raise RuntimeError("Not all servers can be brought up")

        # create a public IP and associate it to gateway
        floating_ip = self.client.floating_ips.create(pool=self.conf.pool)
        self.client.servers.add_floating_ip(self._gateway_id, floating_ip)
        self._gateway_floating_ip = floating_ip
        print "Creating and associating %s" % floating_ip

    def _get_server_info(self, _id):
        """
        get server information (IP, hostname) from server ID

        @param _id: server ID
        """
        server = self.client.servers.get(_id)
        # get ipaddress (there is only 1 item in the dict)
        for key in server.networks:
            ipaddr = server.networks[key][0]
        return (ipaddr, server.name)

    def _setup_chefserver(self):
        """
        execute uploaded scripts to install chef, config knife, upload
        cookbooks, roles, and environments
        """
        for command in self.chefserver_commands:
            cmd.ssh(self.conf.user + "@" + self._chefserver_ip,
                    command, screen_output=True)

    def _checkin_chefserver(self):
        """
        check-in all VMs into chefserver (knife bootstrap), and set their
        environment to be self.conf.prefix
        """
        funcs = []
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        for (ipaddr, hostname) in zip(ipaddrs, hostnames):
            uri = self.conf.user + '@' + self._chefserver_ip
            command = ('/usr/bin/knife bootstrap %s -x %s -N %s -E %s --sudo'
                       % (ipaddr, self.conf.user, hostname, self.conf.prefix))
            func = functools.partial(cmd.ssh, uri, command, screen_output=True,
                                     agent_forwarding=True)
            funcs.append(func)
        self._execute_funcs(funcs)
        # run an empty list to make sure attributes are properly propagated
        self._run_chef_client(ipaddrs)
        # sleep some time
        time.sleep(5)

    def _deploy_network_vxlan(self):
        """
        deploy network-vxlan (recipe) via cookbook openvswitch for all VMs,
        i.e., build VXLAN tunnels with gateway as layer-2 hub and other VMs
        as spokes, and assign ip address and netmask
        """
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        self._add_run_list(hostnames, 'recipe[openvswitch::network-vxlan]')
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        self._run_chef_client(ipaddrs)

    def _deploy_dnsmasq(self):
        """
        deploy dnsmasq (recipe) via cookbook openvswitch for all VMs,
        i.e., install and config on dnsmasq on gateway node, and point all
        VMs to gateway as nameserver
        """
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        self._add_run_list(hostnames, 'recipe[openvswitch::dnsmasq]')
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        self._run_chef_client(ipaddrs)

    def _add_run_list(self, hostnames, item):
        """
        for each server, add an item to its run_list

        @param hostnames: hostnames of specified servers
        @param item: name of the item (e.g., recipe, role, etc)
        """
        funcs = []
        for hostname in hostnames:
            uri = self.conf.user + '@' + self._chefserver_ip
            command = "/usr/bin/knife node run_list add %s %s" % (
                hostname, item)
            func = functools.partial(cmd.ssh, uri, command, screen_output=True,
                                     agent_forwarding=True)
            funcs.append(func)
        self._execute_funcs(funcs)

    def _run_chef_client(self, ipaddrs):
        """
        for each server in the address list, run chef-client for all
        specified cookbooks in its run_list

        @param param: ip addresses of the servers
        """
        funcs = []
        for ipaddr in ipaddrs:
            uri = self.conf.user + '@' + ipaddr
            command = "sudo chef-client"
            func = functools.partial(cmd.ssh, uri, command, screen_output=True,
                                     agent_forwarding=True)
            funcs.append(func)
        self._execute_funcs(funcs)

    def _execute_funcs(self, funcs):
        """
        Execute functions, whether in parallel (via threads) or
            sequential.  If parallel, exceptions of subthreads will be
            collected in a shared queue, and an exception will raised
            in main thread later

        @param funcs: the functions to be executed
        """
        if not self.conf.parallel:
            for func in funcs:
                func()
        else:
            exception_queue = Queue.Queue()
            threads = []
            # create and start all threads
            for func in funcs:
                thread = FuncThread(func, exception_queue)
                threads.append(thread)
                thread.start()
            # wait for all threads to finish
            for thread in threads:
                thread.join()
            # check whether got exception in threads
            got_exception = not exception_queue.empty()
            while not exception_queue.empty():
                thread_name, func_info, exc = exception_queue.get()
                print thread_name, func_info, exc
            if got_exception:
                raise RuntimeError("One or more subthreads got exception")

    def _setup_controller(self):
        """
        deploy OpenStack controller(s) via misc cookbooks
        """
        self._add_run_list([self._controller_name], "role[os-dev-mode]")
        self._add_run_list([self._controller_name],
                           "role[os-controller-combined]")
        self._run_chef_client([self._controller_ip])

    def _setup_workers(self):
        """
        deploy workers via misc cookbooks
        """
        self._add_run_list(self._worker_names, "role[os-dev-mode]")
        self._add_run_list(self._worker_names, "role[os-worker-combined]")
        self._run_chef_client(self._worker_ips)

    def cleanup(self):
        """
        Clean up the whole inception cloud, based on self.conf.prefix
        """
        print "Let's clean up inception cloud '%s'..." % self.conf.prefix
        ## find out servers info
        servers = []
        gateway = None
        gateway_ip = None
        prefix = self.conf.prefix + '-'
        for server in self.client.servers.list():
            if (server.name.startswith(prefix)):
                servers.append(server)
            if server.name == self.conf.prefix + '-gateway':
                gateway = server
                # get ipaddress (there is only 1 item in the dict)
                for key in gateway.networks:
                    if len(gateway.networks[key]) >= 2:
                        gateway_ip = gateway.networks[key][1]
        ## try deleting the floating IP of gateway
        try:
            for floating_ip in self.client.floating_ips.list():
                if floating_ip.ip == gateway_ip:
                    print ("Disassociating and releasing %s" % floating_ip)
                    self.client.servers.remove_floating_ip(gateway,
                                                           floating_ip)
                    self.client.floating_ips.delete(floating_ip)
        except Exception:
            print traceback.format_exc()
        ## try deleting each server
        for server in servers:
            try:
                print 'Deleting %s' % server
                server.delete()
            except Exception:
                print traceback.format_exc()
                continue
        print "Inception cloud '%s' has been cleaned up." % self.conf.prefix


class FuncThread(threading.Thread):
    """
    thread of calling a partial function, based on the regular thread
    by adding a shared-with-others exception queue
    """
    def __init__(self, func, exception_queue):
        threading.Thread.__init__(self)
        self._func = func
        self._exception_queue = exception_queue

    def run(self):
        """
        Call the function, and put exception in queue if any
        """
        try:
            self._func()
        except Exception:
            func_info = (str(self._func.func) + " " + str(self._func.args) +
                         " " + str(self._func.keywords))
            info = (self.name, func_info, traceback.format_exc())
            print info
            self._exception_queue.put(info)


def main():
    """
    program starting point
    """
    # Register options
    CONF.register_opts(cfg_file_opts)
    CONF.register_cli_opts(cli_opts)

    # Processes both config file and cmd line opts
    try:
        CONF(args=sys.argv[1:],
             default_config_files=[os.path.abspath(os.path.dirname(__file__) +
                                                   '/../inception.conf')],
             version='Inception: Version 0.0.1')
    except Exception as e:
        print e
        sys.exit(-2)

    orchestrator = Orchestrator(CONF)

    if CONF.shell:
        # give me a ipython shell
        IPython.embed()
        return
    if CONF.cleanup:
        orchestrator.cleanup()
    else:
        orchestrator.start()

##############################################
if __name__ == "__main__":
    main()
