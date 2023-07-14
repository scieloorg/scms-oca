import csv
import os

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from wagtail.admin import messages
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core.libs import chkcsv
from core_settings.models import Moderation
from infrastructure_directory.search_indexes import InfraStructureIndex
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea

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
    This view function validade a csv file based on a pre definition os the fmt
    file.

    The check_csv_file function check that all of the required columns and data
    are present in the CSV file, and that the data conform to the appropriate
    type and other specifications, when it is not valid return a list with the
    errors.
    """
    errorlist = []
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(InfrastructureDirectoryFile, pk=file_id)

    if request.method == "GET":
        try:
            upload_path = file_upload.attachment.file.path
            cols = chkcsv.read_format_specs(
                os.path.dirname(os.path.abspath(__file__)) + "/chkcsvfmt.fmt",
                True,
                False,
            )
            errorlist = chkcsv.check_csv_file(
                upload_path, cols, True, True, True, False
            )
            if errorlist:
                raise Exception(_("Valication error"))
            else:
                file_upload.is_valid = True
                fp = open(upload_path)
                file_upload.line_count = len(fp.readlines())
                file_upload.save()
        except Exception as ex:
            messages.error(request, _("Valication error: %s") % errorlist)
        else:
            messages.success(request, _("File successfully validated!"))

    return redirect(request.META.get("HTTP_REFERER"))


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
            data = csv.DictReader(csvfile, delimiter=";")

            for line, row in enumerate(data):
                isd = InfrastructureDirectory()
                isd.title = row["Title"]
                isd.link = row["Link"]
                isd.description = row["Description"]

                isd.creator = request.user
                isd.save()

                # Institution
                inst_name = row["Institution Name"]
                if inst_name:
                    inst_country = row["Institution Country"]
                    inst_state = row["Institution State"]
                    inst_city = row["Institution City"]

                    institution = Institution.get_or_create(
                        inst_name, inst_country, inst_state, inst_city, request.user
                    )
                    isd.institutions.add(institution)

                # Thematic Area
                level0 = row["Thematic Area Level0"].strip()
                if level0:
                    level1 = row["Thematic Area Level1"].strip()
                    level2 = row["Thematic Area Level2"].strip()
                    the_area = ThematicArea.get_or_create(
                        level0, level1, level2, request.user
                    )

                    isd.thematic_areas.add(the_area)

                # Keywords
                if row["Keywords"]:
                    for key in row["Keywords"].split("|"):
                        isd.keywords.add(key)

                if row["Classification"]:
                    isd.classification = row["Classification"]

                # Practice
                if row["Practice"]:
                    practice_name = row["Practice"]
                    if Practice.objects.filter(name=practice_name).exists():
                        pratice = Practice.objects.get(name=practice_name)
                        isd.practice = pratice
                    else:
                        messages.error(
                            request, _("Unknown Practice, line: %s") % str(line + 1)
                        )

                # Action
                if row["Action"]:
                    if Action.objects.filter(name__icontains="infraestrutura").exists():
                        isd.action = Action.objects.get(
                            name__icontains="infraestrutura"
                        )

                if row["Source"]:
                    isd.source = row["Source"]

                isd.save()

                # Update de index.
                InfraStructureIndex().update_object(instance=isd)

    except Exception as ex:
        messages.error(request, _("Import error: %s, Line: %s") % (ex, str(line + 2)))
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))


def download_sample(request):
    """
    This view function a CSV sample for model InfraestructureDirectoryFile.
    """
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/example_infra.csv"
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                file_path
            )
            return response
    raise Http404
