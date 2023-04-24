import csv
import os
from datetime import datetime

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from wagtail.admin import messages
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core.libs import chkcsv
from core_settings.models import Moderation
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea

from .models import PolicyDirectory, PolicyDirectoryFile
from .permission_helper import PolicyDirectoryPermissionHelper


class PolicyDirectoryEditView(EditView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PolicyDirectoryCreateView(CreateView):
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

            return PolicyDirectoryPermissionHelper(
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

        if Action.objects.filter(
            name__icontains="políticas públicas e institucionais"
        ).exists():
            instance.action = Action.objects.get(
                name__icontains="políticas públicas e institucionais"
            )

        return instance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_moderation"] = self.must_moderate
        return context


class PolicyDirectoryFileCreateView(CreateView):
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
        file_upload = get_object_or_404(PolicyDirectoryFile, pk=file_id)

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

        Title,Institution,Link,Description,date
        Politica de acesso aberto,Instituição X,http://www.ac.com.br,Diretório internacional de política de acesso aberto

    TODO: This function must be a task.
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(PolicyDirectoryFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    # try:
    with open(file_path, "r") as csvfile:
        data = csv.DictReader(csvfile, delimiter=";")

        for line, row in enumerate(data):
            po = PolicyDirectory()
            po.title = row["Title"]
            po.link = row["Link"]
            po.description = row["Description"]
            if row["Date"]:
                po.date = datetime.strptime(row["Date"], "%d/%m/%Y")
            po.creator = request.user
            po.save()

            # Institution
            inst_name = row["Institution Name"]
            if inst_name:
                inst_country = row["Institution Country"]
                inst_state = row["Institution State"]
                inst_city = row["Institution City"]

                institution = Institution.get_or_create(
                    inst_name, inst_country, inst_state, inst_city, request.user
                )
                po.institutions.add(institution)

            # Thematic Area
            level0 = row["Thematic Area Level0"]
            if level0:
                level1 = row["Thematic Area Level1"]
                level2 = row["Thematic Area Level2"]
                the_area = ThematicArea.get_or_create(
                    level0, level1, level2, request.user
                )

                po.thematic_areas.add(the_area)

            # Keywords
            if row["Keywords"]:
                for key in row["Keywords"].split("|"):
                    po.keywords.add(key)

            if row["Classification"]:
                po.classification = row["Classification"]

            # Practice
            if row["Practice"]:
                practice_name = row["Practice"]
                if Practice.objects.filter(name=practice_name).exists():
                    practice = Practice.objects.get(name=practice_name)
                    po.practice = practice
                else:
                    messages.error(
                        request, _("Unknown Practice, line: %s") % str(line + 2)
                    )

            # Action
            if row["Action"]:
                if Action.objects.filter(
                    name__icontains="políticas públicas e institucionais"
                ).exists():
                    po.action = Action.objects.get(
                        name__icontains="políticas públicas e institucionais"
                    )

            if row["Source"]:
                po.source = row["Source"]

            po.save()
    # except Exception as ex:
    #     messages.error(request, _("Import error: %s, Line: %s") % (ex, str(line + 2)))
    # else:
    #    messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))


def download_sample(request):
    """
    This view function a CSV sample for model PolicyDirectoryFile.
    """
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/example_policy.csv"
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                file_path
            )
            return response
    raise Http404
