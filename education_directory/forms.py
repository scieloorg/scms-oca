from wagtail.admin.forms import WagtailAdminModelForm

from education_directory.search_indexes import EducationIndex


class EducationDirectoryForm(WagtailAdminModelForm):

    def save_all(self, user):
        education_direcotry = super().save(commit=False)

        if self.instance.pk is not None:
            education_direcotry.updated_by = user
        else:
            education_direcotry.creator = user

        self.save()

        # Update de index.
        EducationIndex().update_object(instance=education_direcotry)

        return education_direcotry


class EducationDirectoryFileForm(WagtailAdminModelForm):

    def save_all(self, user):
        education_direcotry_file = super().save(commit=False)

        if self.instance.pk is not None:
            education_direcotry_file.updated_by = user
        else:
            education_direcotry_file.creator = user

        self.save()

        return education_direcotry_file
