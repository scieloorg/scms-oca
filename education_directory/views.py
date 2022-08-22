import csv
import os
from datetime import datetime

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from wagtail.admin import messages

from core.libs import chkcsv
from institution.models import Institution
from usefulmodels.models import Action, Pratice, ThematicArea

from .models import EducationDirectory, EducationDirectoryFile


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

    if request.method == 'GET':
        try:
            upload_path = file_upload.attachment.file.path
            cols = chkcsv.read_format_specs(
                os.path.dirname(os.path.abspath(__file__)) + "/chkcsvfmt.fmt", True, False)
            errorlist = chkcsv.check_csv_file(upload_path, cols, True, True, True, False)
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

    return redirect(request.META.get('HTTP_REFERER'))


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
        with open(file_path, 'r') as csvfile:
            data = csv.DictReader(csvfile)

            for line, row in enumerate(data):
                ed = EducationDirectory()
                ed.title = row['Title']
                ed.link = row['Link']
                ed.description = row['Description']
                if row['Start Date']:
                    ed.start_date = datetime.strptime(row['Start Date'], '%d/%m/%Y')
                if row['End Date']:
                    ed.end_date = datetime.strptime(row['End Date'], '%d/%m/%Y')
                if row['Start Time']:
                    ed.start_time = row['Start Time']
                if row['End Time']:
                    ed.end_time = row['End Time']
                ed.creator = request.user
                ed.save()

                # Institution
                inst_name = row['Institution Name']
                if inst_name:
                    inst_country = row['Institution Country']
                    inst_region = row['Institution Region']
                    inst_state = row['Institution State']
                    inst_city = row['Institution City']

                    institution = Institution.get_or_create(inst_name, inst_country, inst_region,
                                                            inst_state, inst_city, request.user)
                    ed.institutions.add(institution)

                # Thematic Area
                level0 = row['Thematic Area Level0']
                if level0:
                    level1 = row['Thematic Area Level1']
                    level2 = row['Thematic Area Level2']
                    the_area = ThematicArea.get_or_create(level0, level1, level2, request.user)

                    ed.thematic_areas.add(the_area)

                # Keywords
                if row['Keywords']:
                    for key in row['Keywords'].split('|'):
                        ed.keywords.add(key)

                if row['Classification']:
                    ed.classification = row['Classification']

                # Pratice
                if row['Pratice']:
                    pratice_name = row['Pratice']
                    if Pratice.objects.filter(name=pratice_name).exists():
                        pratice = Pratice.objects.get(name=pratice_name)
                        ed.pratice = pratice
                    else:
                        messages.error(request, _("Unknown pratice, line: %s") % str(line + 2))

                # Action
                if row['Action']:
                    action_name = row['Action']
                    if Action.objects.filter(name=action_name).exists():
                        action = Action.objects.get(name=action_name)
                        ed.action = action
                    else:
                        messages.error(request, _("Unknown action, line: %s") % str(line + 2))

                ed.save()
    except Exception as ex:
        messages.error(request, _("Import error: %s, Line: %s") % (ex, str(line + 2)))
    else:
       messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get('HTTP_REFERER'))


def download_sample(request):
    """
    This view function a CSV sample for model EducationDirectoryFile.
    """
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/example_education.csv"
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404


    start_time = models.TimeField(_("Start Time"), max_length=255,
                                  null=True, blank=True)
    end_time = models.TimeField(_("End Time"), max_length=255,
                                  null=True, blank=True)
