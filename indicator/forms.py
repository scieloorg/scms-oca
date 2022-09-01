from wagtail.admin.forms import WagtailAdminModelForm


class IndicatorDirectoryForm(WagtailAdminModelForm):

    def save_all(self, user):
        structure_directory = super().save(commit=False)

        if self.instance.pk is not None:
            structure_directory.updated_by = user
        else:
            structure_directory.creator = user

        self.save()
        self.save_m2m()

        return structure_directory