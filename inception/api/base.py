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

import logging

from novaclient import utils

LOG = logging.getLogger(__name__)


class Manager(utils.HookableMixin):
    """
    Nova-style Managers interact with APIs (e.g. servers, flavors, etc)
    and expose CRUD ops for them.
    """

    resource_class = None

    def __init__(self, api):
        self.api = api

    def _list(self, url, response_key, obj_class=None, body=None):
        _resp, body = self.api.client.get(url)
        if obj_class is None:
            obj_class = self.resource_class

        data = body[response_key]
        return [obj_class(self, res, loaded=True) for res in data if res]

    def _get(self, url, response_key):
        _resp, body = self.api.client.get(url)
        return self.resource_class(self, body[response_key], loaded=True)

    def _create(self, url, body, response_key, return_raw=False, **kwargs):
        self.run_hooks('modify_body_for_create', body, **kwargs)

        _resp, body = self.api.client.post(url, body=body)
        if return_raw:
            return body[response_key]

        return self.resource_class(self, body[response_key])

    def _delete(self, url, body):
        _resp, _body = self.api.client.delete(url, body=body)
