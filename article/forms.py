from wagtail.admin.forms import WagtailAdminModelForm


class ContributorForm(WagtailAdminModelForm):

    def save(self, commit=True):
        co = super().save(commit=False)
        co.affiliations_string = "; ".join(aff.name for aff in co.affiliations.all())

        co.save()
        self.save_m2m()

        return co
