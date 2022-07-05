from wagtail.admin.forms import WagtailAdminModelForm


class EducationDirectoryForm(WagtailAdminModelForm):

    def save_all(self, user):
        education_direcotry = super().save(commit=False)

        if self.instance.pk is not None:
            education_direcotry.updated_by = user
        else:
            education_direcotry.creator = user

        self.save()

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
