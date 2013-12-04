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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django import shortcuts
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tables
from horizon import tabs
from horizon import workflows

from openstack_dashboard import api
import inception.webui.api.inception as iapi
from inception.webui.tables import InceptionInstancesTable
from inception.webui.tabs import InceptionInstanceDetailTabs
from inception.webui.workflows.create_inception_instance import \
    LaunchInceptionInstance
from inception.webui.workflows.create_inception_instance import \
    UpdateInceptionInstance

LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = InceptionInstancesTable
    template_name = 'inception/index.html'

    def has_more_data(self, table):
        LOG.debug("has_more_data called")
        return self._more

    def get_data(self):
        LOG.debug("get_data called")
        marker = self.request.GET.get(
            InceptionInstancesTable._meta.pagination_param, None)
        # Gather our instances
        try:
            instances, self._more = iapi.cloud_list(
                self.request,
                search_opts={'marker': marker,
                             'paginate': True})
        except:
            self._more = False
            instances = []
            exceptions.handle(self.request,
                              _('Unable to retrieve instances.'))
        return instances


class LaunchInceptionInstanceView(workflows.WorkflowView):
    workflow_class = LaunchInceptionInstance

    def get_initial(self):
        LOG.debug("LaunchInceptionInstanceView: get_initial()")
        initial = super(LaunchInceptionInstanceView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class UpdateView(workflows.WorkflowView):
    workflow_class = UpdateInceptionInstance
    success_url = reverse_lazy("horizon:project:instances:index")

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    def get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            instance_id = self.kwargs['instance_id']
            try:
                self._object = api.nova.server_get(self.request, instance_id)
            except:
                redirect = reverse("horizon:project:instances:index")
                msg = _('Unable to retrieve instance details.')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()
        initial.update({'instance_id': self.kwargs['instance_id'],
                        'name': getattr(self.get_object(), 'name', '')})
        return initial


class DetailView(tabs.TabView):
    tab_group_class = InceptionInstanceDetailTabs
    template_name = 'project/instances/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["instance"] = self.get_data()
        return context

    def get_data(self):
        if not hasattr(self, "_instance"):
            try:
                instance_id = self.kwargs['instance_id']
                instance = iapi.cloud_get(self.request, instance_id)
                instance.security_groups = api.network.server_security_groups(
                    self.request, instance_id)
            except:
                redirect = reverse('horizon:project:instances:index')
                exceptions.handle(self.request,
                                  _('Unable to retrieve details for '
                                    'instance "%s".') % instance_id,
                                  redirect=redirect)
            self._instance = instance
        return self._instance

    def get_tabs(self, request, *args, **kwargs):
        instance = self.get_data()
        return self.tab_group_class(request, instance=instance, **kwargs)
