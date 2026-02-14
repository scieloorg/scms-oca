from wagtail.admin.forms import WagtailAdminModelForm


class TransformationScriptForm(WagtailAdminModelForm):
    def save_all(self, user):
        obj = super().save(commit=False)

        if self.instance.pk is not None:
            obj.updated_by = user
        else:
            obj.creator = user

        self.save()

        return obj
