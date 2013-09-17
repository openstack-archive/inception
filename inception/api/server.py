#!/usr/bin/env python

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

# TODO(AJF): add configuration, noted throughout
# TODO(AJF): add database scrubbing code for when it gets out of sync with
#            reality (e.g. due to out-of-band Inception Cloud manipulation)

import anyjson
import logging
import threading
import uuid
from wsgiref.simple_server import make_server

from routes import Mapper
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator, CHAR

from inception.orchestrator import Orchestrator


logging.basicConfig()
LOG = logging.getLogger(__name__)

# TODO(AJF): make db name/loc config item
engine = create_engine('sqlite:///./inception.db', echo=True)
Session = sessionmaker(bind=engine)

Base = declarative_base()

#
# Route Mappping
#

mapper = Mapper()

# URLs contain project_id for future use.

mapper.connect("create", "/{project_id}/att-inception-clouds",
               controller="OrchestratorAdapter", action="create",
               conditions=dict(method=["POST"]))
mapper.connect("index", "/{project_id}/att-inception-clouds",
               controller="OrchestratorAdapter", action="index",
               conditions=dict(method=["GET"]))
mapper.connect("delete", "/{project_id}/att-inception-clouds/{id}",
               controller="OrchestratorAdapter", action="delete",
               conditions=dict(method=["DELETE"]))
mapper.connect("show", "/{project_id}/att-inception-clouds/{id}",
               controller="OrchestratorAdapter", action="show",
               conditions=dict(method=["GET"]))


class AsyncOrchestrator(threading.Thread):
    """Thread sub-class for invoking (long running) Orchestrator.start() or
       Orchestrator.cleanup() methods."""

    def __init__(self, orch_opts, cmd, inception_cloud=None):
        threading.Thread.__init__(self)
        self.opts = orch_opts           # Capture Orchestrator (config) options
        self.cmd = cmd                  # cmd = create|destroy

        if not inception_cloud is None:
            # InceptionCloud object provided to constructor (delete case)
            self.ic = inception_cloud   # database view of things
        else:
            self.ic = InceptionCloud()  # Create new IC obj (create case)

        self.session = Session()        # SQLAlchemy session obj

    def _make_orchestrator(self, d):
        """Create an Orchestrator Object from a dictionary of parameters."""
        # NB: certain values are required even for Orchestrator.cleanup()
        # to function.  Those are not allowed a default value here.  Values
        # that aren't required for cleanup() (and probably not stored in the
        # database) are permitted a default since they don't matter.
        return Orchestrator(
            prefix=d['prefix'],
            num_workers=d['num_workers'],
            atomic=False,
            parallel=True,
            sdn=False,
            chef_repo=d.get('chef_repo', ''),
            chef_repo_branch=d.get('chef_repo_branch', ''),
            # TODO(AJF): key
            ssh_keyfile=None,
            pool=d.get('pool', ''),
            user=d.get('user', ''),
            image=d['image'],
            chefserver_image=d.get('chefserver_image', ''),
            flavor=d.get('flavor', ''),
            gateway_flavor=d.get('gateway_flavor', ''),
            key_name=d.get('key_name', ''),
            security_groups=d.get('security_groups', ''),
            src_dir='../bin/',
            dst_dir=d.get('dst_dir', ''),
            # TODO(AJF): end-to-end transport of userdata ("customization scripts")
            # from horizon requires more work.
            userdata='../bin/userdata.sh.template',
            timeout=25 * 60,
            poll_interval=5)

    def _create(self):
        """Create an Orchestrator object and use it to create an
           Inception Cloud."""

        # Create Orchestrator object from opts originating in request JSON
        orchestrator = self._make_orchestrator(self.opts)

        #  Start initializing InceptionCloud object to persist data of interest
        self.ic.status = 'Active'
        self.ic.power_state = 'Building'
        self.ic.save(orchestrator)
        self.session.add(self.ic)
        self.session.commit()

        # Run Orchestrator.start()
        try:
            orchestrator.start()
        except Exception as e:
            # NOTE(AJF): presently Orchestrator.start() swallows its own 
            # exceptions so this part is dead code
            self.ic.status = 'Error'
            self.ic.power_state = 'Failed'
            self.session.commit()
            LOG.exception("Orchestrator.start() failed")
            return

        LOG.info("Orchestrator.start() completed.  Inception cloud %s created." %
            self.ic.id)

        # Copy info generated by running Orchestrator.start() into database
        self.ic.save(orchestrator)
        self.ic.status = 'Active'
        self.ic.power_state = 'Running'
        self.session.commit()

    def _destroy(self):
        """Create an Orchestrator object from an InceptionCloud object
           retrieved from the database and use it to destroy an actual
           Inception Cloud."""

        # Create Orchestrator object from InceptionCloud object
        orchestrator = self._make_orchestrator(self.ic.__dict__)

        # Run orchestrator
        self.ic.task = 'Deleting'
        self.session.commit()

        try:
            orchestrator.cleanup()
        except Exception as e:
            # NOTE(AJF): presently orch obj swallows its own exceptions
            # so this part is dead code
            self.ic.status = 'Error'
            self.ic.power_state = 'Failed'
            self.session.commit()
            LOG.exception("Orchestrator.cleanup() failed")
            return

        LOG.info("Orchestrator.cleanup() completed.  Inception cloud %s destroyed." %
            self.ic.id)

        self.session.delete(self.ic)
        self.session.commit()

    def run(self):
        if self.cmd == 'create':
            self._create()
        elif self.cmd == 'destroy':
            self._destroy()
        else:
            LOG.critical("Unrecognized command: %s", self.cmd)

#
# Database
#


class GUID(TypeDecorator):
    """Backend-neutral GUID type from Type Decorator Recipes
       http://docs.sqlalchemy.org/en/rel_0_8/core/types.html"""

    impl = CHAR

    def load_dialect_impl(self, dialect):
        td = UUID() if dialect.name == 'postgresql' else CHAR(32)
        return dialect.type_descriptor(td)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:   # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):
        return value if value is None else uuid.UUID(value)


class Worker(Base):
    """Models Worker Nodes in the Inception Cloud to persist information about
       them.  Required since IC:worker cardinality is 1:N"""
    __tablename__ = 'inception_workers'

    id = Column(GUID, primary_key=True)     # OpenStack worker VM id
    ic_id = Column(GUID, ForeignKey("inception_clouds.id"))
    cloud = relationship("InceptionCloud",
                         backref=backref("worker_ids", order_by=id),
                         cascade="all, delete, delete-orphan",
                         single_parent=True)

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return ("<Workers('%s', from_ic='%s' )>" % (self.id, self.ic_id,))


class InceptionCloud(Base):
    """Models Inception Clouds to persist information about them.
    Not all data that is an input to the creation of an Orchestrator object
    is worthy of persistence and some data which is an output of running
    Orchestrator.start() is worthy of persistence."""
    __tablename__ = 'inception_clouds'

    id = Column(GUID, primary_key=True)
    prefix = Column(String)
    num_workers = Column(Integer)
    image = Column(String)
    gw_id = Column(String)
    gw_floating_ip = Column(String)
    chef_id = Column(String)
    chef_ip = Column(String)
    controller_id = Column(String)
    controller_ip = Column(String)
    size = Column(String)
    keypair = Column(String)
    status = Column(String)
    task = Column(String)
    power_state = Column(String)

    def __init__(self):
        self.id = uuid.uuid4()      # Generate our own IC id
        self.worker_ids = []

    def __repr__(self):
        return "<InceptionCloud('%s')>" % (self.id,)

    def save(self, orch):
        """Save information contained in the orchestrator obj that was
           obtained by the successful completion of the start() method."""
        self.prefix = orch.prefix
        self.num_workers = orch.num_workers
        self.image = orch.image
        self.gw_id = orch._gateway_id
        self.gw_floating_ip = orch._gateway_floating_ip #.ip
        self.chef_id = orch._chefserver_id
        self.chef_ip = orch._chefserver_ip
        self.controller_id = orch._controller_id
        self.controller_ip = orch._controller_ip
        self.worker_ids = [Worker(wid) for wid in orch._worker_ids]
        # self.size =
        # self.keypair =

    def to_dict(self):
        """Returns InceptionCloud attributes of interest in dict form."""

        def hexOrNone(id):
            #TODO(AJF): be more careful with db input so that all ids are of same
            # type and this function can be simplified/eliminated.
            if id is None:
                return id
            if type(id) is unicode:
                return uuid.UUID(id).hex
            return id.hex

        return {
            'id': hexOrNone(self.id),
            'prefix': self.prefix,
            'num_workers': self.num_workers,
            'image': self.image,
            'gw_id': hexOrNone(self.gw_id),
            'gw_floating_ip': self.gw_floating_ip,
            'chef_id': hexOrNone(self.chef_id),
            'chef_ip': self.chef_ip,
            'controller_id': hexOrNone(self.controller_id),
            'controller_ip': self.controller_ip,
            'worker_ids': [wid.id.hex for wid in self.worker_ids],
            'size': self.size,
            'keypair': self.keypair,
            'status': self.status,
            'task': self.task,
            'power_state': self.power_state,
        }

#
# WSGI to Orchestrator Adaptor
#

def read_request_body(environ):
    """Read and return the request body from a WSGI environment."""
    content_length = int(environ['CONTENT_LENGTH'])
    return environ['wsgi.input'].read(content_length)


class OrchestratorAdapter(object):
    """A class to implement the Restful API for Orchestrator.
       Each method implements an individual API call and is itself a WSGI
       application."""

    def index(self, environ, start_response, route_vars):
        """GET /: All Inception Clouds known to system."""
        session = Session()
        inception_clouds = session.query(InceptionCloud).all()
        if inception_clouds is None:
            status = '404 NOTFOUND'
            response_headers = [('Content-type', 'text/json')]
            start_response(status, response_headers)
            return [anyjson.serialize({})]

        ds = [ic.to_dict() for ic in inception_clouds]
        status = '200 OK'
        response_headers = [('Content-type', 'text/json')]
        start_response(status, response_headers)
        return [anyjson.serialize(dict(clouds=ds))]

    def create(self, environ, start_response, route_vars):
        """POST /: Create new Inception Cloud."""
        request_body = read_request_body(environ)
        d = anyjson.deserialize(request_body)

        ao = AsyncOrchestrator(d, 'create')
        ao.start()

        status = '200 OK'
        response_headers = [('Content-type', 'text/json')]
        start_response(status, response_headers)
        result = {'cloud':{'id': ao.ic.id.hex,}}
        return [anyjson.serialize(result)]

    def delete(self, environ, start_response, route_vars):
        """DELETE /id: Delete specific Inception Cloud."""
        id = route_vars['id']
        session = Session()
        inception_cloud = session.query(
            InceptionCloud).filter(InceptionCloud.id == id).first()
        if inception_cloud is None:
            status = '404 NOTFOUND'
            response_headers = [('Content-type', 'text/json')]
            start_response(status, response_headers)
            return [anyjson.serialize({})]

        d = inception_cloud.to_dict()
        ao = AsyncOrchestrator(d, 'destroy', inception_cloud)
        ao.start()

        status = '200 OK'
        response_headers = [('Content-type', 'text/json')]
        start_response(status, response_headers)
        result = {'action': 'delete', 'id': d['id'], 'prefix': d['prefix']}
        return [anyjson.serialize(result)]

    def show(self, environ, start_response, route_vars):
        """GET /id: Show Inception Cloud details for specific cloud."""
        id = route_vars['id']
        session = Session()
        inception_cloud = session.query(
            InceptionCloud).filter(InceptionCloud.id == id).first()

        if inception_cloud is None:
            status = '404 NOTFOUND'
            response_headers = [('Content-type', 'text/json')]
            start_response(status, response_headers)
            return [anyjson.serialize({})]

        d = inception_cloud.to_dict()
        status = '200 OK'
        response_headers = [('Content-type', 'text/json')]
        start_response(status, response_headers)
        return [anyjson.serialize(dict(cloud=d))]

#
# WSGI Application
#

controllers = {'OrchestratorAdapter': OrchestratorAdapter()}


def application(environ, start_response):
    """Simple top-level WSGI application"""
    route_vars = mapper.match(environ['PATH_INFO'], environ)
    if route_vars is None:
        status = '404 NOTFOUND'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return []

    controller = controllers[route_vars['controller']]
    action = getattr(controller, route_vars['action'])

    return action(environ, start_response, route_vars)


def app_factory(global_config, **local_config):
    """This function wraps the simple app above so that
       paste.deploy can use it."""
    return application


def server_factory(global_conf, host, port):
    """Paste's example server factory.
       Use wsgiref's server because it supports HTTP's DELETE method
       whereas paste.deploy's wsgiutils one does not."""
    port = int(port)

    def serve(app):
        s = make_server(host=host, port=port, app=app)
        s.serve_forever()

    return serve

#
# Main Program
#

if __name__ == '__main__':
    Base.metadata.create_all(engine)    # Create db if not already
