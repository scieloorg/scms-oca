from wagtail.admin.forms import WagtailAdminModelForm


class InstitutionForm(WagtailAdminModelForm):

    def save_all(self, user):
        institution = super().save(commit=False)

        if self.instance.pk is not None:
            institution.updated_by = user
        else:
            institution.creator = user

        self.save()

        return institution
