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

"""
Inception Cloud Interface  -- "in the style of nova client"
"""

from novaclient import base
from inception.api import base as local_base


class Cloud(base.Resource):

    def start(self):
        self.manager.start(self)

    def delete(self):
        self.manager.delete(self)


class CloudManager(local_base.Manager):

    resource_class = Cloud

    def get(self, cloud):
        return self._get("/att-inception-clouds/%s" % base.getid(cloud),
                         "cloud")

    def list(self):     # , detailed=True, search_opts=None):
        return self._list("/att-inception-clouds", "clouds")

    def create(self, prefix, num_workers, flavor, gateway_flavor, image, user,
               pool, key_name, security_groups, chef_repo, chef_repo_branch,
               chefserver_image, dst_dir, userdata, OS_AUTH_URL, OS_PASSWORD,
               OS_TENANT_ID, OS_TENANT_NAME, OS_USERNAME, **kwargs):
        body = dict(prefix=prefix, num_workers=num_workers,
                    flavor=flavor, gateway_flavor=gateway_flavor, image=image,
                    user=user, pool=pool, key_name=key_name,
                    security_groups=security_groups, chef_repo=chef_repo,
                    chef_repo_branch=chef_repo_branch,
                    chefserver_image=chefserver_image, dst_dir=dst_dir,
                    userdata=userdata, OS_AUTH_URL=OS_AUTH_URL,
                    OS_PASSWORD=OS_PASSWORD, OS_TENANT_ID=OS_TENANT_ID,
                    OS_TENANT_NAME=OS_TENANT_NAME, OS_USERNAME=OS_USERNAME,)
        self._create("/att-inception-clouds", body, 'cloud')

    def delete(self, cloud, OS_AUTH_URL, OS_PASSWORD, OS_TENANT_ID,
               OS_TENANT_NAME, OS_USERNAME):
        body = dict(OS_AUTH_URL=OS_AUTH_URL, OS_PASSWORD=OS_PASSWORD,
                    OS_TENANT_ID=OS_TENANT_ID, OS_TENANT_NAME=OS_TENANT_NAME,
                    OS_USERNAME=OS_USERNAME,)
        self._delete("/att-inception-clouds/%s" % base.getid(cloud), body)
