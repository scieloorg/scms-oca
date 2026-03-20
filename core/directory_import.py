import os
from datetime import datetime
from itertools import zip_longest

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from wagtail.admin import messages

from core.libs import chkcsv
from institution.models import Institution
from usefulmodels.models import Action, Practice, ThematicArea


def get_row_value(row, *column_names):
    """
    Return the first non-empty CSV value among the given columns.
    """
    fallback_value = ""

    for column_name in column_names:
        if column_name not in row:
            continue

        value = (row.get(column_name) or "").strip()
        if not fallback_value:
            fallback_value = value
        if value:
            return value

    return fallback_value


def split_pipe_values(value, keep_empty=False):
    """
    Split pipe-separated values and normalize surrounding whitespace.
    """
    if not value:
        return []

    values = [item.strip() for item in value.split("|")]
    if keep_empty:
        return values

    return [item for item in values if item]


def combine_pipe_columns(*column_values):
    """
    Combine pipe-separated columns by position.
    """
    split_columns = [
        split_pipe_values(column_value, keep_empty=True)
        for column_value in column_values
    ]

    combined_values = []
    for values in zip_longest(*split_columns, fillvalue=""):
        normalized_values = tuple(value.strip() for value in values)
        if any(normalized_values):
            combined_values.append(normalized_values)

    return combined_values


def sync_related_items(related_manager, items):
    """
    Replace related items with the imported set.
    """
    related_manager.clear()
    for item in items:
        related_manager.add(item)


def sync_keywords(keyword_manager, values):
    """
    Replace imported keywords.
    """
    keyword_manager.set(split_pipe_values(values))


def build_institutions(
    row,
    user,
    name_columns=("Institution Name",),
    country_columns=("Institution Country",),
    state_columns=("Institution State",),
    city_columns=("Institution City",),
):
    """
    Create or fetch institutions combining pipe-separated columns by position.
    """
    institution_values = combine_pipe_columns(
        get_row_value(row, *name_columns),
        get_row_value(row, *country_columns),
        get_row_value(row, *state_columns),
        get_row_value(row, *city_columns),
    )
    institutions = []
    for inst_name, inst_country, inst_state, inst_city in institution_values:
        if not inst_name:
            continue
        institutions.append(
            Institution.get_or_create(
                inst_name,
                inst_country,
                inst_state,
                inst_city,
                user,
            )
        )
    return institutions


def build_thematic_areas(
    row,
    user,
    level0_columns=("Thematic Area Level0",),
    level1_columns=("Thematic Area Level1",),
    level2_columns=("Thematic Area Level2",),
):
    """
    Create or fetch thematic areas combining pipe-separated columns by position.
    """
    thematic_area_values = combine_pipe_columns(
        get_row_value(row, *level0_columns),
        get_row_value(row, *level1_columns),
        get_row_value(row, *level2_columns),
    )

    thematic_areas = []
    for level0, level1, level2 in thematic_area_values:
        if not level0:
            continue

        thematic_areas.append(ThematicArea.get_or_create(level0, level1, level2, user))

    return thematic_areas


def get_directory_instance(model_class, record_id):
    """
    Get existing directory instance by ID or create new one.

    Args:
        model_class: The model class (e.g., EducationDirectory)
        record_id: The record ID from CSV

    Returns:
        Instance of the model class
    """
    if record_id:
        try:
            return model_class.objects.get(id=record_id)
        except model_class.DoesNotExist:
            pass
    return model_class()


def get_practice(row):
    """
    Get Practice object from CSV row.

    Args:
        row: Dictionary with CSV row data

    Returns:
        Practice object if found, None otherwise
    """
    practice_name = get_row_value(row, "Practice")
    if practice_name:
        try:
            return Practice.objects.get(name=practice_name)
        except Practice.DoesNotExist:
            return None
    return None


def get_action(row, action_filter=None):
    """
    Get Action object from CSV row with optional filter.

    Args:
        row: Dictionary with CSV row data
        action_filter: Optional string to filter actions by name (case-insensitive)

    Returns:
        Action object if found, None otherwise
    """
    if get_row_value(row, "Action"):
        if action_filter:
            return Action.objects.filter(name__icontains=action_filter).first()
    return None


def set_common_fields(instance, row, user, action_filter=None):
    """
    Set common fields on a directory instance from CSV row.

    Args:
        instance: Directory instance to update
        row: Dictionary with CSV row data
        user: User creating/updating the record
        action_filter: Optional string to filter actions by name
    """
    instance.title = get_row_value(row, "Title")
    instance.link = get_row_value(row, "Link")
    instance.description = get_row_value(row, "Description")
    instance.creator = user

    if classification := get_row_value(row, "Classification"):
        instance.classification = classification

    if practice := get_practice(row):
        instance.practice = practice

    if action := get_action(row, action_filter):
        instance.action = action

    if source := get_row_value(row, "Source"):
        instance.source = source


def get_dates_and_times(instance_directory, row):
    """
    Set start and end date/time fields on an instance_directory instance based on a CSV row.

    Args:
        instance_directory: EducationDirectory instance whose attributes will be updated.
        row: Dictionary containing data from the current CSV row.

    Returns:
        dict: Dictionary containing the processed date and time values.
    """
    date_time_data = {}

    if hasattr(instance_directory, "start_date") and row.get("Start Date"):
        instance_directory.start_date = format_date(row["Start Date"], "%d/%m/%Y")
        date_time_data["start_date"] = instance_directory.start_date

    if hasattr(instance_directory, "end_date") and row.get("End Date"):
        instance_directory.end_date = format_date(row["End Date"], "%d/%m/%Y")
        date_time_data["end_date"] = instance_directory.end_date

    if hasattr(instance_directory, "start_time") and row.get("Start Time"):
        instance_directory.start_time = row["Start Time"]
        date_time_data["start_time"] = instance_directory.start_time

    if hasattr(instance_directory, "end_time") and row.get("End Time"):
        instance_directory.end_time = row["End Time"]
        date_time_data["end_time"] = instance_directory.end_time

    return date_time_data


def format_date(date, format):
    if date and isinstance(str, format):
        return datetime.strptime(date, format)


def validate_directory_file(request, file_model_class, format_file_path):
    """
    Universal validation function for directory CSV files.

    Validates a CSV file based on a pre-defined format specification.
    Checks that all required columns and data are present and conform to
    the appropriate type and specifications.

    Args:
        request: Django request object
        file_model_class: The file model class (e.g., EducationDirectoryFile)
        format_file_path: Absolute path to the .fmt file for validation

    Returns:
        HttpResponseRedirect to the referer page
    """
    if request.method != "GET":
        return redirect(request.META.get("HTTP_REFERER"))

    file_id = request.GET.get("file_id")
    if not file_id:
        messages.error(request, _("File not informed."))
        return redirect(request.META.get("HTTP_REFERER"))

    file_upload = get_object_or_404(file_model_class, pk=file_id)
    upload_path = file_upload.attachment.file.path

    try:
        cols = chkcsv.read_format_specs(format_file_path, True, False)
        errorlist = chkcsv.check_csv_file(upload_path, cols, True, True, True, False)

        if errorlist:
            messages.error(request, _("Validation error") + f": {errorlist}")
            return redirect(request.META.get("HTTP_REFERER"))

        with open(upload_path) as uploaded_file:
            file_upload.is_valid = True
            file_upload.line_count = len(uploaded_file.readlines())
            file_upload.save()

    except Exception as ex:
        messages.error(request, _("Validation error: %s") % str(ex))
    else:
        messages.success(request, _("File successfully validated!"))

    return redirect(request.META.get("HTTP_REFERER"))


def download_sample_file(sample_file_path):
    """
    Universal function to download a CSV sample file.

    Args:
        sample_file_path: Absolute path to the sample CSV file

    Returns:
        HttpResponse with the CSV file or raises Http404
    """

    if os.path.exists(sample_file_path):
        with open(sample_file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                sample_file_path
            )
            return response
    raise Http404
