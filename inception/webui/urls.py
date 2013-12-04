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

from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url

from inception.webui.views import DetailView
from inception.webui.views import UpdateView
from inception.webui.views import IndexView
from inception.webui.views import LaunchInceptionInstanceView


INSTANCES = r'^(?P<instance_id>[^/]+)/%s$'
VIEW_MOD = 'horizon.inception.views'

urlpatterns = patterns(
    VIEW_MOD,
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^launch$', LaunchInceptionInstanceView.as_view(), name='launch'),
    url(r'^(?P<instance_id>[^/]+)/$', DetailView.as_view(), name='detail'),
    url(r'^(?P<instance_id>[^/]+)/update$', UpdateView.as_view(),
        name='update'),
)
