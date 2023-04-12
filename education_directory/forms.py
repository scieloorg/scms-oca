from wagtail.admin.forms import WagtailAdminModelForm

from education_directory.search_indexes import EducationIndex


class EducationDirectoryForm(WagtailAdminModelForm):
    def save_all(self, user):
        education_directory = super().save(commit=False)

        if self.instance.pk is not None:
            education_directory.updated_by = user
        else:
            education_directory.creator = user

        self.save()
        self.save_m2m()

        # Update de index.
        EducationIndex().update_object(instance=education_directory)

        return education_directory


class EducationDirectoryFileForm(WagtailAdminModelForm):
    def save_all(self, user):
        education_directory_file = super().save(commit=False)

        if self.instance.pk is not None:
            education_directory_file.updated_by = user
        else:
            education_directory_file.creator = user

        self.save()

        return education_directory_file
