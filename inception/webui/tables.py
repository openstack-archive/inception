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

from django.core import urlresolvers
from django.template.defaultfilters import filesizeformat
from django.template.defaultfilters import title
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _

import logging

from openstack_dashboard import api
from horizon import tables
from horizon.utils.filters import replace_underscores

import inception.webui.api.inception as iapi
from inception.webui.tabs import InceptionInstanceDetailTabs
from inception.webui.tabs import LogTab

LOG = logging.getLogger(__name__)


ACTIVE_STATES = ("ACTIVE",)
SNAPSHOT_READY_STATES = ("ACTIVE", "SHUTOFF")

POWER_STATES = {
    0: "NO STATE",
    1: "RUNNING",
    2: "BLOCKED",
    3: "PAUSED",
    4: "SHUTDOWN",
    5: "SHUTOFF",
    6: "CRASHED",
    7: "SUSPENDED",
    8: "FAILED",
    9: "BUILDING",
}

PAUSE = 0
UNPAUSE = 1
SUSPEND = 0
RESUME = 1


def is_deleting(instance):
    task_state = getattr(instance, "OS-EXT-STS:task_state", None)
    if not task_state:
        return False
    return task_state.lower() == "deleting"


class LaunchLink(tables.LinkAction):
    name = "launch"
    verbose_name = _("Launch Inception Instance")
    url = "horizon:project:inception:launch"
    classes = ("btn-launch", "ajax-modal")

    def allowed(self, request, datum):
        try:
            limits = api.nova.tenant_absolute_limits(request, reserved=True)

            instances_available = limits['maxTotalInstances'] \
                - limits['totalInstancesUsed']
            cores_available = limits['maxTotalCores'] \
                - limits['totalCoresUsed']
            ram_available = limits['maxTotalRAMSize'] - limits['totalRAMUsed']

            if instances_available <= 0 or cores_available <= 0 \
                    or ram_available <= 0:
                if "disabled" not in self.classes:
                    self.classes = [c for c in self.classes] + ['disabled']
                    self.verbose_name = string_concat(self.verbose_name, ' ',
                                                      _("(Quota exceeded)"))
            else:
                self.verbose_name = _("Launch Inception Instance")
                classes = [c for c in self.classes if c != "disabled"]
                self.classes = classes
        except:
            LOG.exception("Failed to retrieve quota information")
            # If we can't get the quota information, leave it to the
            # API to check when launching

        return True  # The action should always be displayed


class EditInstance(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Inception Instance")
    url = "horizon:project:inception:update"
    classes = ("ajax-modal", "btn-edit")

    def get_link_url(self, project):
        return self._get_link_url(project, 'instance_info')

    def _get_link_url(self, project, step_slug):
        base_url = urlresolvers.reverse(self.url, args=[project.id])
        param = urlencode({"step": step_slug})
        return "?".join([base_url, param])

    def allowed(self, request, instance):
        return not is_deleting(instance)


class LogLink(tables.LinkAction):
    name = "log"
    verbose_name = _("View Orchestrator Log")
    url = "horizon:project:inception:instances:detail"
    classes = ("btn-log",)

    def allowed(self, request, instance=None):
        return instance.status in ACTIVE_STATES and not is_deleting(instance)

    def get_link_url(self, datum):
        base_url = super(LogLink, self).get_link_url(datum)
        tab_query_string = LogTab(
            InceptionInstanceDetailTabs).get_query_string()
        return "?".join([base_url, tab_query_string])


class TerminateInstance(tables.BatchAction):
    name = "terminate"
    action_present = _("Terminate Inception")
    action_past = _("Scheduled termination of")
    data_type_singular = _("Instance")
    data_type_plural = _("Instances")
    classes = ('btn-danger', 'btn-terminate')

    def allowed(self, request, instance=None):
        return True

    def action(self, request, obj_id):
        iapi.cloud_delete(request, obj_id)


class InstancesFilterAction(tables.FilterAction):

    def filter(self, table, instances, filter_string):
        """ Naive case-insensitive search. """
        q = filter_string.lower()
        return [instance for instance in instances
                if q in instance.name.lower()]


def get_power_state(instance):
    return getattr(instance, "power_state", 'unknown')


STATUS_DISPLAY_CHOICES = (
    ("resize", "Resize/Migrate"),
    ("verify_resize", "Confirm or Revert Resize/Migrate"),
    ("revert_resize", "Revert Resize/Migrate"),
)


TASK_DISPLAY_CHOICES = (
    ("image_snapshot", "Snapshotting"),
    ("resize_prep", "Preparing Resize or Migrate"),
    ("resize_migrating", "Resizing or Migrating"),
    ("resize_migrated", "Resized or Migrated"),
    ("resize_finish", "Finishing Resize or Migrate"),
    ("resize_confirming", "Confirming Resize or Nigrate"),
    ("resize_reverting", "Reverting Resize or Migrate"),
    ("unpausing", "Resuming"),
)


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, instance_id):
        cloud = iapi.cloud_get(request, instance_id)
        return cloud


class InceptionInstancesTable(tables.DataTable):
    """ See: openstack_dashboard/dashboards/project/instances/tables.py"""

    TASK_STATUS_CHOICES = (
        (None, True),
        ("none", True)
    )

    STATUS_CHOICES = (
        ("active", True),
        ("shutoff", True),
        ("suspended", True),
        ("paused", True),
        ("error", False),
    )

    prefix = tables.Column("prefix",
                           link=("horizon:project:inception:detail"),
                           verbose_name=_("Prefix"))
    n_workers = tables.Column("num_workers", verbose_name=_("No. of Workers"))

    status = tables.Column("status",
                           filters=(title, replace_underscores),
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)
    task = tables.Column("task_state",
                         verbose_name=_("Task"),
                         filters=(title, replace_underscores),
                         status=True,
                         status_choices=TASK_STATUS_CHOICES,
                         display_choices=TASK_DISPLAY_CHOICES)
    state = tables.Column(get_power_state,
                          filters=(title, replace_underscores),
                          verbose_name=_("Power State"))

    class Meta:
        name = "inception_instances"
        verbose_name = _("Inception Instances")
        multi_select = True
        #table_actions = (myact1, myact2,)
        #row_actions = (myact1, myact2,)
        row_class = UpdateRow
        table_actions = (LaunchLink, TerminateInstance, InstancesFilterAction)
        row_actions = (EditInstance, LogLink, TerminateInstance)
