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

import anyjson
import logging
import requests

LOG = logging.getLogger(__name__)

from inception.api import clouds


class HTTPClient(object):
    USER_AGENT = 'python-inceptionclient'

    def __init__(self, project_id=None, endpoint=None):
        self.project_id = project_id
        self.endpoint = endpoint

    def request(self, method, url, **kwargs):
        # Fix up request headers
        hdrs = kwargs.get('headers', {})
        hdrs['Accept'] = 'application/json'
        hdrs['User-Agent'] = self.USER_AGENT

        # If request has a body, treat it as JSON
        if 'body' in kwargs:
            hdrs['Content-Type'] = 'application/json'
            kwargs['data'] = anyjson.serialize(kwargs['body'])
            del kwargs['body']

        kwargs['headers'] = hdrs

        resp = requests.request(method,
                                (self.endpoint + self.project_id) + url,
                                **kwargs)

        if resp.text:
            if resp.status_code == 400:
                if ('Connection refused' in resp.text or
                        'actively refused' in resp.text):
                    raise exceptions.ConnectionRefused(resp.text)
            try:
                body = anyjson.deserialize(resp.text)
            except ValueError:
                pass
                body = None
        else:
            body = None

        return resp, body

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self.request('POST', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request('DELETE', url, **kwargs)


class Client(object):
    def __init__(self, project_id=None,
                 endpoint='http://127.0.0.1:7653/'):
        #TODO(forrest-r): make IC server endpoint a config item
        self.client = HTTPClient(project_id=project_id, endpoint=endpoint)
        self.clouds = clouds.CloudManager(self)

if __name__ == '__main__':
    import sys
    # edit as needed and execute directly to test
    client = Client()
    cloud_list = client.clouds.list()

    print "cloud_list=", cloud_list
