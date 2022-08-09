from wagtail.admin.forms import WagtailAdminModelForm


class LocationForm(WagtailAdminModelForm):

    def save_all(self, user):
        location = super().save(commit=False)

        if self.instance.pk is not None:
            location.updated_by = user
        else:
            location.creator = user

        self.save()

        return location
