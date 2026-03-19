import csv
import os

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from wagtail.admin import messages
from wagtail_modeladmin.views import CreateView, EditView

from core import tasks
from core.directory_import import (
    build_institutions,
    build_thematic_areas,
    download_sample_file,
    format_date,
    get_directory_instance,
    get_row_value,
    set_common_fields,
    sync_keywords,
    sync_related_items,
    validate_directory_file,
)
from core_settings.models import Moderation
from usefulmodels.models import Action

from .models import InfrastructureDirectory, InfrastructureDirectoryFile
from .permission_helper import InfrastructureDirectoryPermissionHelper


class InfrastructureDirectoryCreateView(CreateView):
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

            return InfrastructureDirectoryPermissionHelper(
                model=self.model
            ).must_be_moderate(self.request.user)

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

    def get_instance(self):
        instance = super().get_instance()

        if Action.objects.filter(name__icontains="infraestrutura").exists():
            instance.action = Action.objects.get(name__icontains="infraestrutura")

        return instance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_moderation"] = self.must_moderate
        return context


class InfrastructureDirectoryEditView(EditView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        # if user is a staff must no moderate
        if self.request.user.is_staff:
            return False

        return InfrastructureDirectoryPermissionHelper(
            model=self.model
        ).must_be_moderate(self.request.user)

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)

        # check if have moderation
        if self.must_moderate:
            if self.get_moderation():
                # fix the status to ``TO MODERATE``
                self.object.record_status = "TO MODERATE"
                self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class InfrastructureDirectoryFileCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


def validate(request):
    """
    Validate CSV file for InfrastructureDirectory import.
    """
    format_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "chkcsvfmt.fmt"
    )
    return validate_directory_file(
        request, InfrastructureDirectoryFile, format_file_path
    )


def import_file(request):
    """
    This view function import the data from a CSV file.

    Something like this:

        Title,Link,Description
        FAPESP,http://www.fapesp.com.br,primary

    TODO: This function must be a task.
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(InfrastructureDirectoryFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(
                csvfile, delimiter=settings.DIRECTORY_IMPORT_DELIMITER
            )

            for line, row in enumerate(data):
                record_id = get_row_value(row, "Id")
                isd = get_directory_instance(InfrastructureDirectory, record_id)
                set_common_fields(
                    isd, row, request.user, action_filter="infraestrutura"
                )
                isd.date = format_date(get_row_value(row, "date"), "%d/%m/%Y")
                isd.save()
                sync_related_items(
                    isd.institutions,
                    build_institutions(row, request.user),
                )
                sync_related_items(
                    isd.thematic_areas,
                    build_thematic_areas(row, request.user),
                )
                sync_keywords(isd.keywords, row.get("Keywords"))

                isd.save()
    except Exception as ex:
        messages.error(
            request,
            _(f"Import error: {ex}, Line: {line + 2}")
        )
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))


def download_sample(request):
    """
    Download CSV sample file for InfrastructureDirectory import.
    """
    sample_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "example_infra.csv"
    )
    return download_sample_file(sample_file_path)
