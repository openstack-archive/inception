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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from inception.webui.api import inception as iapi
from openstack_dashboard import api


class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "inception_overview"
    template_name = ("project/instances/"
                     "_detail_overview.html")

    def get_context_data(self, request):
        return {"instance": self.tab_group.kwargs['instance']}


class LogTab(tabs.Tab):
    name = _("Log")
    slug = "inception_log"
    template_name = "project/instances/_detail_log.html"
    preload = False

    def get_context_data(self, request):
        instance = self.tab_group.kwargs['instance']
        try:
            data = 'log goes here'
            # TODO(forrest-r): augment if log storage/retrieval supported
            # iapi.server_console_output(request,
            #                            instance.id,
            #                            tail_length=35)
        except:
            data = _('Unable to get log for instance "%s".') % instance.id
            exceptions.handle(request, ignore=True)
        return {"instance": instance,
                "console_log": data}


class InceptionInstanceDetailTabs(tabs.TabGroup):
    slug = "inception_instance_details"
    tabs = (OverviewTab, LogTab)
    sticky = True
