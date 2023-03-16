from wagtail.admin.forms import WagtailAdminModelForm

from event_directory.search_indexes import EventIndex


class EventDirectoryForm(WagtailAdminModelForm):
    def save_all(self, user):
        event_directory = super().save(commit=False)

        if self.instance.pk is not None:
            event_directory.updated_by = user
        else:
            event_directory.creator = user

        self.save()

        # Update de index.
        EventIndex().update_object(instance=event_directory)

        return event_directory


class EventDirectoryFileForm(WagtailAdminModelForm):
    def save_all(self, user):
        event_directory_file = super().save(commit=False)

        if self.instance.pk is not None:
            event_directory_file.updated_by = user
        else:
            event_directory_file.creator = user

        self.save()

        return event_directory_file
