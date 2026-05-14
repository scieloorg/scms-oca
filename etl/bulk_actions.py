from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from wagtail.snippets.bulk_actions.snippet_bulk_action import SnippetBulkAction
from wagtail.snippets.permissions import get_permission_name

from etl.models import EtlItemProcess


class ResetToPendingBulkAction(SnippetBulkAction):
    models = [EtlItemProcess]
    display_name = _("Reset to pending")
    action_type = "reset_to_pending"
    aria_label = _("Reset selected ETL items to pending")
    template_name = "etl/admin/bulk_actions/reset_to_pending.html"
    action_priority = 40

    def check_perm(self, item):
        if getattr(self, "can_change_items", None) is None:
            self.can_change_items = self.request.user.has_perm(
                get_permission_name("change", self.model)
            )
        return self.can_change_items

    @classmethod
    def execute_action(cls, objects, **kwargs):
        rows = EtlItemProcess.objects.reset_to_pending(
            [item.pk for item in objects]
        )
        return rows, 0

    def get_success_message(self, num_parent_objects, num_child_objects):
        return ngettext(
            "%(count)d ETL item reset to pending.",
            "%(count)d ETL items reset to pending.",
            num_parent_objects,
        ) % {"count": num_parent_objects}
