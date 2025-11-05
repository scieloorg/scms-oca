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


@require_POST
def data_view(request):
    # Read data source from request GET parameters
    data_source = request.GET.get("data_source")
    if not data_source:
        return JsonResponse({"error": "Missing data_source parameter in request URL"}, status=400)
    
    # Read filters from the request body sent by the indicator form
    body_text = request.body.decode()
    payload = json.loads(body_text) if body_text else {}

    filters = payload.get("filters", {})
    filters = dict(filters)
    
    # Read language query operator
    language_query_operator = filters.pop("document_language_operator", None)

    # Read country query operator
    country_query_operator = filters.pop("country_operator", None)

    # Read study unit
    study_unit = filters.pop("study_unit", None)

    # Read breakdown variable
    breakdown_variable = filters.pop("breakdown_variable", None)

    # Extract index name from data source
    index_name = controller.get_index_name_from_data_source(data_source)

    # Get field mapping for the data source
    field_settings = constants.DSNAME_TO_FIELD_SETTINGS.get(data_source)

    # Build the query to filter documents
    query = controller.build_query(
        filters, 
        field_settings, 
        data_source,
        language_query_operator,
        country_query_operator
    )

    # FIXME: move this logic to controller
    # Choose main aggregation
    aggs = {}
    if breakdown_variable:
        if study_unit == "citation":
            aggs = controller.build_breakdown_citation_per_year_aggs(field_settings, breakdown_variable)
        elif study_unit == "document":
            aggs = controller.build_breakdown_documents_per_year_aggs(field_settings, breakdown_variable, data_source)
    else:
        if study_unit == "citation":
            aggs = controller.build_citations_per_year_aggs()
        elif study_unit == "document":
            aggs = controller.build_documents_per_year_aggs(data_source)

    body = {"size": 0, "query": query, "aggs": aggs}

    # Execute search
    try:
        res = controller.es.search(index=index_name, body=body)
    except Exception:
        return JsonResponse({"error": "Error executing search"}, status=500)

    # FIXME: move this logic to controller
    # Parse response
    data = {}
    if breakdown_variable:
        if study_unit == "citation":
            data = controller.parse_breakdown_citation_per_year_response(res)
        elif study_unit == "document":
            data = controller.parse_breakdown_documents_per_year_response(res)
        data["breakdown_variable"] = breakdown_variable
    else:
        if study_unit == "citation":
            data = controller.parse_citations_per_year_response(res)
        elif study_unit == "document":
            data = controller.parse_documents_per_year_response(res)

    return JsonResponse(data)


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


def journal_view(request):
    context = {
        "data_source": "journal_metrics",
        "data_source_display_name": _("Journal Metrics"),
    }
    return render(request, "indicator.html", context)


def search_item(request):
    # Read query parameters
    q = request.GET.get("q", "")
    req_data_source_name = request.GET.get("data_source", "journal_metrics")
    req_field_name = request.GET.get("field_name", "journal")

    # Extract index name from data source
    index_name = controller.get_index_name_from_data_source(req_data_source_name)

    # Get field settings for the data source
    field_settings = controller.get_field_settings(req_data_source_name)
    
    # Determine field name
    fl_name = (field_settings.get(req_field_name, {}).get("index_field_name", req_field_name))

    # Determine if the field supports search-as-you-type
    fl_support_search_as_you_type = field_settings.get(req_field_name, {}).get("filter", {}).get("search_as_you_type", False)

    # Build search body
    if fl_support_search_as_you_type:
        body = controller.build_search_as_you_type_body(fl_name, q)
    else:
        body = controller.build_term_search_body(fl_name, q)

    # Execute search
    try:
        res = controller.es.search(index=index_name, body=body)
    except Exception:
        return JsonResponse({"error": "Error executing search"}, status=500)

    # Parse results
    try:
        parsed_results = controller.parse_search_item_response(res)
    except Exception:
        return JsonResponse({"error": "Error parsing search results"}, status=500)

    return JsonResponse({"results": parsed_results})


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
