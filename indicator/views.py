import json
import logging

from django.http import HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from wagtail_modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation

from .permission_helper import IndicatorPermissionHelper
from .metrics.controller import get_indicator_data


logger = logging.getLogger(__name__)


@require_POST
def chart_data_view(request):
    try:
        body_text = request.body.decode()
        payload = json.loads(body_text) if body_text else {}

        data_source_name = payload.get("data_source") or request.GET.get("data_source")
        if not data_source_name:
            logger.error("Missing data_source parameter in request")
            return JsonResponse({"error": "Missing data_source parameter"}, status=400)

        filters = payload.get("filters", {})
        study_unit = payload.get("study_unit", "document")

        data, error = get_indicator_data(data_source_name, filters, study_unit)

        if error:
            logger.error(f"Error getting indicator data: {error}")
            return JsonResponse({"error": error}, status=500)

        if not data:
            logger.error("No data returned from get_indicator_data")
            return JsonResponse({"error": "No data available"}, status=500)

        return JsonResponse(data)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error in chart_data_view: {e}")
        return JsonResponse({"error": str(e)}, status=500)


class IndicatorDirectoryEditView(EditView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        if self.request.user.is_staff:
            return False
        return IndicatorPermissionHelper(model=self.model).must_be_moderate(self.request.user)

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        if self.must_moderate and self.object.record_status != "PUBLISHED":
            if self.get_moderation():
                self.object.record_status = "TO MODERATE"
                self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class IndicatorDirectoryCreateView(CreateView):
    """
    DEPRECATED
    """
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        if self.get_moderation():
            if self.request.user.is_staff:
                return False
            return IndicatorPermissionHelper(model=self.model).must_be_moderate(self.request.user)

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        if self.must_moderate:
            moderation = self.get_moderation()
            if moderation:
                self.object.record_status = "TO MODERATE"
                self.object.save()
                if moderation.send_mail:
                    user_email = self.get_moderation().moderator.email or None
                    group_mails = [
                        user.email
                        for user in self.get_moderation().group_moderator.user_set.all()
                        if user.email
                    ] if self.get_moderation().group_moderator else []
                    tasks.send_mail(
                        _("Novo conteúdo para moderação - %s" % self.model._meta.verbose_name.title()),
                        render_to_string(
                            "email/moderate_email.html",
                            {"obj": self.object, "user": self.request.user, "request": self.request},
                        ),
                        to_list=[user_email],
                        bcc_list=group_mails,
                        html=True,
                    )
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_moderation"] = self.must_moderate
        return context
