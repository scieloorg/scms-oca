import json

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation

from . import constants, controller
from .permission_helper import IndicatorPermissionHelper


# Create a filters cache to avoid repeated ES queries
FILTERS_CACHE = {}


@require_GET
def filters_view(request):
    # Get data source from request
    data_source = request.GET.get('data_source')

    # Extract index name from data source
    index_name = controller.get_index_name_from_data_source(data_source)

    # Use cached filters if available
    if index_name in FILTERS_CACHE:
        return JsonResponse(FILTERS_CACHE[index_name])

    # Get aggregations based on data source
    field_settings = constants.DSNAME_TO_FIELD_SETTINGS.get(data_source)
    if not field_settings:
        return JsonResponse({"error": "Invalid data source"}, status=400)

    # FIXME: move this logic to controller
    # Build aggregations
    aggs = {}
    for form_field_name, field_info in field_settings.items():
        name = field_info.get("index_field_name")
        size = field_info.get("filter", {}).get("size")
        order = field_info.get("filter", {}).get("order")

        terms = {"field": name, "size": size}

        if order:
            terms["order"] = order

        aggs[form_field_name] = {"terms": terms}

    # Build ES query body
    body = {"size": 0, "aggs": aggs}

    # Execute ES query
    try:
        res = controller.es.search(index=index_name, body=body)
        filters = {k: [b["key"] for b in v["buckets"]] for k, v in res["aggregations"].items()}

        # Cache the filters
        FILTERS_CACHE[index_name] = filters

        return JsonResponse(filters)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def world_view(request):
    selected_filters = request.GET.dict()
    context = {
        "data_source": "world",
        "data_source_display_name": _("Scientific Production - World"),
        "selected_filters": selected_filters,
    }
    return render(request, "indicator.html", context)


def brazil_view(request):
    context = {
        "data_source": "brazil",
        "data_source_display_name": _("Scientific Production - Brazil"),
    }
    return render(request, "indicator.html", context)


def scielo_view(request):
    context = {
        "data_source": "scielo",
        "data_source_display_name": _("Scientific Production - SciELO Network"),
    }
    return render(request, "indicator.html", context)


def social_view(request):
    context = {
        "data_source": "social",
        "data_source_display_name": _("Social Production"),
    }
    return render(request, "indicator.html", context)


class IndicatorDirectoryEditView(EditView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        # if user is a staff must no moderate
        if self.request.user.is_staff:
            return False

        return IndicatorPermissionHelper(model=self.model).must_be_moderate(
            self.request.user
        )

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)

        # check if have moderation and if the record_status is diferent from ``PUBLISHED``
        if self.must_moderate and self.object.record_status != "PUBLISHED":
            if self.get_moderation():
                # fix the status to ``TO MODERATE``
                self.object.record_status = "TO MODERATE"
                self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class IndicatorDirectoryCreateView(CreateView):
    def get_moderation(self):
        # check if exists a moderation and if is enabled
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        if self.get_moderation():
            # if user is a staff must no moderate
            if self.request.user.is_staff:
                return False

            return IndicatorPermissionHelper(model=self.model).must_be_moderate(
                self.request.user
            )

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)

        # check if have moderation
        if self.must_moderate:
            moderation = self.get_moderation()

            if moderation:
                # fix the status to ``TO MODERATE``
                self.object.record_status = "TO MODERATE"
                self.object.save()

                # check if must send e-mail
                if moderation.send_mail:
                    # get user
                    user_email = self.get_moderation().moderator.email or None
                    group_mails = []

                    if self.get_moderation().group_moderator:
                        # get group
                        group_mails = [
                            user.email
                            for user in self.get_moderation().group_moderator.user_set.all()
                            if user.email
                        ]
                    tasks.send_mail(
                        _(
                            "Novo conteúdo para moderação - %s"
                            % self.model._meta.verbose_name.title()
                        ),
                        render_to_string(
                            "email/moderate_email.html",
                            {
                                "obj": self.object,
                                "user": self.request.user,
                                "request": self.request,
                            },
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
