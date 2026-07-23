from django.core.exceptions import ValidationError
from wagtail.admin.forms import WagtailAdminModelForm


class WorldRegionsUploadForm(WagtailAdminModelForm):
    def full_clean(self):
        super().full_clean()

        if self.errors or "file" not in self.changed_data:
            return

        try:
            self.instance.validate_and_load_mapping()
        except ValidationError as error:
            self.add_error(None, error)

    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance._state.adding:
            instance.creator = self.for_user
        else:
            instance.updated_by = self.for_user

        if commit:
            instance.save()
            self.save_m2m()

        return instance
