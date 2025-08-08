import csv
import os
from datetime import datetime

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.template.loader import render_to_string
from django.conf import settings
from wagtail.admin import messages
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core.libs import chkcsv
from core_settings.models import Moderation
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea
from .permission_helper import EducationDirectoryPermissionHelper

from .models import EducationDirectory, EducationDirectoryFile


class EducationDirectoryCreateView(CreateView):
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

            return EducationDirectoryPermissionHelper(
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

        if Action.objects.filter(name__icontains="educação / capacitação").exists():
            instance.action = Action.objects.get(
                name__icontains="educação / capacitação"
            )

        return instance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_moderation"] = self.must_moderate
        return context


class EducationDirectoryEditView(EditView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        # if user is a staff must no moderate
        if self.request.user.is_staff:
            return False

        return EducationDirectoryPermissionHelper(model=self.model).must_be_moderate(
            self.request.user
        )

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)

        # check if have moderation
        if self.must_moderate:
            if self.get_moderation():
                # fix the status to ``TO MODERATE``
                self.object.record_status = "TO MODERATE"
                self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class EducationDirectoryFileCreateView(CreateView):
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
        file_upload = get_object_or_404(EducationDirectoryFile, pk=file_id)

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
        file_upload = get_object_or_404(EducationDirectoryFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(csvfile, delimiter=settings.DIRECTORY_IMPORT_DELIMITER)

            for line, row in enumerate(data):

                record_id = row.get("Id", "").strip()
                if record_id and EducationDirectory.objects.filter(id=record_id).exists():
                    ed = EducationDirectory.objects.get(id=record_id)
                else:
                    ed = EducationDirectory()

                ed.title = row["Title"]
                ed.link = row["Link"]
                ed.description = row["Description"]
                if row["Start Date"]:
                    ed.start_date = datetime.strptime(row["Start Date"], "%d/%m/%Y")
                if row["End Date"]:
                    ed.end_date = datetime.strptime(row["End Date"], "%d/%m/%Y")
                if row["Start Time"]:
                    ed.start_time = row["Start Time"]
                if row["End Time"]:
                    ed.end_time = row["End Time"]
                ed.creator = request.user
                ed.save()

                # Institution
                inst_name = row["Institution Name"].strip()
                if inst_name:
                    inst_country = row["Institution Country"].strip()
                    inst_state = row["Institution State"].strip()
                    inst_city = row["Institution City"].strip()

                    institution = Institution.get_or_create(
                        inst_name, inst_country, inst_state, inst_city, request.user
                    )
                    ed.institutions.add(institution)

                # Thematic Area
                level0 = row["Thematic Area Level0"].strip()
                if level0:
                    level1 = row["Thematic Area Level1"].strip()
                    level2 = row["Thematic Area Level2"].strip()
                    the_area = ThematicArea.get_or_create(
                        level0, level1, level2, request.user
                    )

                    ed.thematic_areas.add(the_area)

                # Keywords
                if row["Keywords"]:
                    for key in row["Keywords"].split("|"):
                        ed.keywords.add(key)

                if row["Classification"]:
                    ed.classification = row["Classification"]

                # Practice
                if row["Practice"]:
                    practice_name = row["Practice"]
                    if Practice.objects.filter(name=practice_name).exists():
                        practice = Practice.objects.get(name=practice_name)
                        ed.practice = practice
                    else:
                        messages.error(
                            request, _("Unknown Practice, line: %s") % str(line + 2)
                        )

                # Action = educação / capacitação"
                if row["Action"]:
                    if Action.objects.filter(
                        name__icontains="educação / capacitação"
                    ).exists():
                        ed.action = Action.objects.get(
                            name__icontains="educação / capacitação"
                        )

                if row["Source"]:
                    ed.source = row["Source"]

                ed.save()
    except Exception as ex:
        messages.error(request, _("Import error: %s, Line: %s") % (ex, str(line + 2)))
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))


def download_sample(request):
    """
    This view function a CSV sample for model EducationDirectoryFile.
    """
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/example_education.csv"
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                file_path
            )
            return response
    raise Http404

    start_time = models.TimeField(
        _("Start Time"), max_length=255, null=True, blank=True
    )
    end_time = models.TimeField(_("End Time"), max_length=255, null=True, blank=True)
