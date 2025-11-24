import json

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation
from search_gateway import data_sources
from search_gateway.controller import get_filters_data

from .search import controller, utils
from .permission_helper import IndicatorPermissionHelper


@require_POST
def data_view(request):
    data_source_name = request.GET.get("data_source")
    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)

    body_text = request.body.decode()
    payload = json.loads(body_text) if body_text else {}
    filters = payload.get("filters", {})

    data, error = controller.get_indicator_data(data_source_name, dict(filters))
    if error:
        status_code = 503 if error == "Service unavailable" else 400 if error == "Invalid data_source" else 500
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


def indicator_view(request, data_source_name):
    if data_source_name not in data_sources.DATA_SOURCES or data_source_name == "journal_metrics":
        return JsonResponse({"error": "Invalid data_source"}, status=404)

    data_source = data_sources.DATA_SOURCES[data_source_name]

    cleaned_filters = utils.clean_form_filters(request.GET.dict())
    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.get("display_name"),
        "applied_filters": cleaned_filters,
    }
    context["applied_filters_json"] = json.dumps(context["applied_filters"])
    return render(request, "indicator.html", context)


def journal_metrics_view(request):
    data_source_name = "journal_metrics"
    data_source = data_sources.DATA_SOURCES[data_source_name]

    cleaned_get_filters = utils.clean_form_filters(request.GET.dict())
    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.get("display_name"),
        "applied_filters": cleaned_get_filters,
    }

    context["filters_data"], _ = get_filters_data(data_source_name)

    if request.method == "POST":
        form_filters = request.POST.dict()
        cleaned_post_filters = utils.clean_form_filters(form_filters.copy())
        context["applied_filters"].update(cleaned_post_filters)

        ranking_data, error = controller.get_journal_metrics_data(form_filters)
        if error:
            context["error"] = _("Error executing search: %s") % error
        else:
            context["ranking_data"] = ranking_data

    context["applied_filters_json"] = json.dumps(context["applied_filters"])
    return render(request, "indicator.html", context)


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
