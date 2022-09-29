from wagtail.admin.forms import WagtailAdminModelForm


class IndicatorDirectoryForm(WagtailAdminModelForm):

    def save_all(self, user):
        indicator = super().save(commit=False)

        if self.instance.pk is not None:
            indicator.updated_by = user
        else:
            indicator.creator = user

        self.save()
        self.save_m2m()

        return indicator


class VersioningForm(WagtailAdminModelForm):

    def save_all(self, user):
        versioning = super().save(commit=False)

        if self.instance.pk is not None:
            versioning.updated_by = user
        else:
            versioning.creator = user

        self.save()
        self.save_m2m()

        return versioning