import os
import csv
from datetime import datetime
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.utils.translation import gettext as _

from wagtail.admin import messages

from core.libs import chkcsv

from .models import EventDirectoryFile, EventDirectory


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
        file_upload = get_object_or_404(EventDirectoryFile, pk=file_id)

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

        Event,Link,Description,Organization
        Seminário X,http://www.sem.com.br,Seminário XPTO,SciELO

    TODO: This function must be a task.
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(EventDirectoryFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        with open(file_path, 'r') as csvfile:
            data = csv.DictReader(csvfile)

            for row in data:
                di = EventDirectory()
                di.event = row['Event']
                di.link = row['Link']
                di.description = row['Description']
                di.organization = row['Organization']
                di.start_date = datetime.strptime(row['Start Date'], '%d/%m/%Y')
                di.end_date = datetime.strptime(row['End Date'], '%d/%m/%Y')
                di.start_time = row['Start Time']
                di.end_time = row['End Time']
                di.creator = request.user
                di.save()
    except Exception as ex:
        messages.error(request, _("Import error: %s") % ex)
    else:
       messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get('HTTP_REFERER'))


def download_sample(request):
    """
    This view function a CSV sample for model EventDirectoryFile.
    """
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/example_event.csv"
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404
