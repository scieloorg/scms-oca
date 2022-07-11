from wagtail.admin.forms import WagtailAdminModelForm


class DisclosureDirectoryForm(WagtailAdminModelForm):

    def save_all(self, user):
        disclosure_direcotry = super().save(commit=False)

        if self.instance.pk is not None:
            disclosure_direcotry.updated_by = user
        else:
            disclosure_direcotry.creator = user

        self.save()

        return disclosure_direcotry


class DisclosureDirectoryFileForm(WagtailAdminModelForm):

    def save_all(self, user):
        disclosure_direcotry_file = super().save(commit=False)

        if self.instance.pk is not None:
            disclosure_direcotry_file.updated_by = user
        else:
            disclosure_direcotry_file.creator = user

        self.save()

        return disclosure_direcotry_file
